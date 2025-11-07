from fastapi import APIRouter, Depends, status, HTTPException, Query 
from sqlalchemy.orm import Session
from typing import List, Optional 
from .database import get_db
from datetime import datetime, timezone 
import logging
from .schemas import EventSerializer, EventCreate 
from .models import Event
from .managers import EventManager 
from .tasks import generate_recurring_events 

router = APIRouter(prefix="/events", tags=["Events & Celery Testing"])
logger = logging.getLogger(__name__)

@router.post(
    "/initial",
    response_model=EventSerializer,
    status_code=status.HTTP_201_CREATED,
    summary="Create the initial base event for recurrence",
)
def create_initial_event(
    event_in: EventCreate, 
    db: Session = Depends(get_db)
):
    """Creates the initial base event"""
    manager = EventManager(db)
    tz_utc = timezone.utc
    
    event_in.start_date = event_in.start_date.replace(tzinfo=tz_utc, microsecond=0)
    event_in.end_date = event_in.end_date.replace(tzinfo=tz_utc, microsecond=0)
    event_in.registration_deadline = event_in.registration_deadline.replace(tzinfo=tz_utc, microsecond=0)

    if event_in.registration_deadline >= event_in.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration deadline ({event_in.registration_deadline}) must be strictly before the start date ({event_in.start_date})."
        )
    base_title = event_in.title.split(' - ')[0].strip()
    month_year = event_in.start_date.strftime('%B %Y')
    event_in.title = f"{base_title} - {month_year}"
    db_event = manager.create_base_event(event_in)
    return db_event


@router.get(
    "/",
    response_model=List[EventSerializer],
    summary="Get all events with optional filtering and pagination"
)
def get_all_events(
    db: Session = Depends(get_db),
    is_active: Optional[bool] = Query(None, description="Filter by event activity status"),
    skip: int = Query(0, description="Number of events to skip (offset)"),
    limit: int = Query(100, description="Maximum number of events to return (limit)")
):
    """Gets all events"""
    query = db.query(Event)
    if is_active is not None:
        query = query.filter(Event.is_active == is_active)
    query = query.order_by(Event.start_date)
    query = query.offset(skip).limit(limit)
    
    events = query.all()
    return events


@router.post(
    "/celery/trigger-manual",
    summary="Manually trigger Celery task (for instant testing)",
    status_code=status.HTTP_202_ACCEPTED
)
def trigger_celery_task():
    task = generate_recurring_events.delay()
    logger.info(f"Celery task generated. Task ID: {task.id}")
    return {
        "message": "Celery task successfully triggered.",
        "task_id": task.id
    }