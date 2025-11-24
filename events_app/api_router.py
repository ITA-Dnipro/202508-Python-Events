from fastapi import APIRouter, Depends, status, HTTPException, Query 
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional 
from .database import get_db
from datetime import datetime, timezone, time
import logging
from .schemas import EventSerializer, EventCreate, EventRegistrationSerializer, EventRegistrationCreate
from .models import Event, EventRegistration
from .dependencies import get_current_user, CurrentUser
from .managers import EventManager 
from .tasks import generate_recurring_events 
import pytz

KYIV_TZ = pytz.timezone('Europe/Kyiv')

router = APIRouter(prefix="/events")
logger = logging.getLogger(__name__)

def to_aware_utc_midnight(dt_date):
    """Converts a date to 00:00:00 Kyiv time, then to UTC."""
    tz_utc = timezone.utc
    dt_naive = datetime.combine(dt_date, time(0, 0, 0))
    dt_aware_kyiv = KYIV_TZ.localize(dt_naive)
    return dt_aware_kyiv.astimezone(tz_utc).replace(microsecond=0)

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
    
    event_in.start_date = to_aware_utc_midnight(event_in.start_date)
    event_in.end_date = to_aware_utc_midnight(event_in.end_date)
    event_in.registration_deadline = to_aware_utc_midnight(event_in.registration_deadline)
    if event_in.registration_deadline >= event_in.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration deadline ({event_in.registration_deadline}) must be strictly before the start date ({event_in.start_date})."
        )
    base_title = event_in.title.split(' - ')[0].strip()
    month_year = event_in.start_date.strftime('%B %Y')
    event_in.title = f"{base_title} - {month_year}"
    
    try:
        db_event = manager.create_base_event(event_in)
        db.commit()
        return db_event
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An event with the specified unique constraints already exists."
        )


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
    '''Manually triggers the Celery task to generate recurring events.'''
    task = generate_recurring_events.delay()
    logger.info(f"Celery task generated. Task ID: {task.id}")
    return {
        "message": "Celery task successfully triggered.",
        "task_id": task.id
    }

@router.post(
    "/{event_id}/register",
    response_model=EventRegistrationSerializer,
    status_code=status.HTTP_201_CREATED,
    summary="Register current user for an event"
)

def register_event(
    event_id: int,
    registration_data: EventRegistrationCreate, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user) 
):
    """
    Registers a user for an event checking deadlines and active status.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    if not event.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is not possible. Event is inactive."
        )
    
    now = datetime.now(timezone.utc)
    if now > event.registration_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is closed for this event."
        )

    if hasattr(current_user, "allowed_roles") and registration_data.role not in current_user.allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have a '{registration_data.role}' profile."
        )

    try:
        new_registration = EventRegistration(
            event_id=event.id,
            user_id=current_user.id,
            role=registration_data.role,
        )
        db.add(new_registration)
        db.commit()
        db.refresh(new_registration)        
        return new_registration

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already registered for this event."
        )

@router.delete(
    "/{event_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel registration"
)
def cancel_registration(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Cancels the current user's registration for the specified event.
    """
    registration = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == current_user.id
    ).first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Registration not found"
        )

    db.delete(registration)
    db.commit()
    return None


@router.get(
    "/{event_id}/participants",
    response_model=List[EventRegistrationSerializer],
    summary="List all participants"
)
def list_participants(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Shows a list of all participants for the event.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    participants = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.status == "registered"
    ).all()
    
    return participants