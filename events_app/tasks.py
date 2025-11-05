from .celery_app import celery_app
from .database import SessionLocal 
from .managers import EventManager 
from .models import Event
from datetime import datetime, timezone
from sqlalchemy import desc

@celery_app.task(name='tasks.generate_recurring_events')
def generate_recurring_events():
    """
    Celery task to generate recurring events based on existing ones.
    """
    
    db = SessionLocal()
    created_count = 0
    
    try:
        manager = EventManager(db)
        all_events = db.query(Event).order_by(Event.start_date).all()
        latest_events = {}
        
        for event in all_events:
            base_title = event.title.split(' - ')[0].strip()
            if base_title not in latest_events or event.start_date > latest_events[base_title].start_date:
                latest_events[base_title] = event

        now = datetime.now(timezone.utc)
        
        for base_title, latest_event in latest_events.items():
            if now > latest_event.start_date:
                
                new_dates = manager._calculate_next_dates(latest_event)
                month_year = new_dates['start_date'].strftime('%B %Y')
                new_event_title_check = f"{base_title} - {month_year}"

                exists = db.query(Event).filter(Event.title == new_event_title_check).first()
                
                if not exists:
                    manager.create_next_event(latest_event)
                    db.commit()
                    created_count += 1

    except Exception as e:
        db.rollback()
        print(f"Cannot generate recurring events: {e}")
        raise
    finally:
        db.close()