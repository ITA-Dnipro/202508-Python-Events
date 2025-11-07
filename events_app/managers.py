from typing import Optional
from datetime import timedelta, timezone
from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta
from .models import Event 
from .schemas import EventCreate

class EventManager:
    """
    Class to manage event creation and scheduling.
    """
    def __init__(self, db: Session):
        self.db = db

    def _calculate_next_dates(self, previous_event: Event) -> dict:
            """
            Calculates new dates based on the following rules:
            1. Repetition always occurs 1 month later.
            2. Event duration is fixed at 5 days.
            3. Registration deadline is the moment the new event starts.
            """
            date_shift = relativedelta(months=1) 
            start_date_with_tz = previous_event.start_date.replace(tzinfo=timezone.utc)
            new_start_date = start_date_with_tz + date_shift
            duration = timedelta(days=5) 
            new_end_date = new_start_date + duration
            one_second = timedelta(seconds=1)
            new_registration_deadline = new_start_date - one_second
            
            return {
                "start_date": new_start_date,
                "end_date": new_end_date,
                "registration_deadline": new_registration_deadline,
            }

    def create_next_event(self, previous_event: Event) -> Optional[Event]:
        """
        Creates the next event.
        """
        new_dates = self._calculate_next_dates(previous_event)
        month_year = new_dates['start_date'].strftime('%B %Y')
        
        new_event_title = f"{previous_event.title.split(' - ')[0].strip()} - {month_year}"
        new_event_theme = previous_event.theme 
        
        new_event = Event(
            title=new_event_title,
            theme=new_event_theme,
            description="will be generated based on theme of new_event_theme",
            start_date=new_dates['start_date'],
            end_date=new_dates['end_date'],
            registration_deadline=new_dates['registration_deadline'],
            is_active=True,
        )
        self.db.add(new_event)
        
        return new_event
    

    def create_base_event(self, event_data: EventCreate) -> Event:
        """
        Creates a base event from provided data.
        """
        db_event = Event(**event_data.dict()) 
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event


    def get_all_events(self) -> list[Event]:
            """
            Retrieves all events from the database.
            Returns a list of SQLAlchemy Event objects.
            """
            return self.db.query(Event).all()