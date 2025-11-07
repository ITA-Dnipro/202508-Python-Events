from .celery_app import celery_app
from .database import SessionLocal 
from .managers import EventManager 
from .models import Event
from datetime import datetime, timezone
from sqlalchemy import desc
import logging
logger = logging.getLogger(__name__)

@celery_app.task(name='events_app.tasks.generate_recurring_events')
def generate_recurring_events():
    """
    Celery task to generate recurring events based on existing ones.
    """

    db = SessionLocal()
    created_count = 0
    now = datetime.now(timezone.utc).replace(microsecond=0) 
    try:
        manager = EventManager(db)
        all_events = db.query(Event).order_by(Event.start_date).all()
        latest_events = {}
        for event in all_events:
            base_title = event.title.split(' - ')[0].strip()
            if base_title not in latest_events or event.start_date > latest_events[base_title].start_date:
                latest_events[base_title] = event
        
        for base_title, latest_event in latest_events.items():
            latest_db_date = latest_event.start_date
            if latest_db_date.tzinfo is not None:
                latest_db_date = latest_db_date.astimezone(timezone.utc)
            else:
                latest_db_date = latest_db_date.replace(tzinfo=timezone.utc)
            latest_db_date = latest_db_date.replace(microsecond=0)
            if now > latest_db_date: 
                
                new_dates = manager._calculate_next_dates(latest_event)
                month_year = new_dates['start_date'].strftime('%B %Y')
                new_event_title_check = f"{base_title} - {month_year}"

                exists = db.query(Event).filter(Event.title == new_event_title_check).first()
                if not exists:
                    manager.create_next_event(latest_event)
                    db.commit()
                    created_count += 1
                    logger.info(f"Generated new event: {new_event_title_check}")
                else:
                    logger.info(f"Skipping event generation: {new_event_title_check} already exists.")

    except Exception as e:
        db.rollback()
        logger.error(f"Cannot generate recurring events. Rolled back transaction. Error: {e}")
        raise 
    finally:
        db.close()
        logger.info(f"Recurring event generation finished. Created {created_count} new events.")