from typing import Optional, List, Dict
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dateutil.relativedelta import relativedelta
from .models import Event 
from .schemas import EventCreate

class EventManager:
    def __init__(self, db: Session):
        self.db = db

    def _calculate_next_dates(self, previous_event: Event) -> dict:
        """
        Calculates new dates based on the following rules:
        1. Repetition always occurs 1 month later.
        2. Event duration is fixed at 5 days.
        3. Registration deadline is 1 second before the new event starts.
        """
        date_shift = relativedelta(months=1) 
        start_date_with_tz = previous_event.start_date
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

    def create_base_event(self, event_data: EventCreate) -> Event:
        """
        Creates a base event from provided data and handles potential duplicates.
        """
        db_event = Event(**event_data.dict())
        try:
            self.db.add(db_event)
            self.db.commit()
            self.db.refresh(db_event)
            return db_event
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Duplicate or invalid event: {e}") 

    def create_next_event(self, previous_event: Event) -> Optional[Event]:
        """
        Creates the next event.
        """
        new_dates = self._calculate_next_dates(previous_event)
        month_year = new_dates['start_date'].strftime('%B %Y')
        
        base_title = previous_event.title.split(' - ')[0].strip()
        new_event_title = f"{base_title} - {month_year}"
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
        
        try:
            self.db.add(new_event)
            self.db.commit()
            self.db.refresh(new_event)
            return new_event
        except IntegrityError:
            self.db.rollback()
            return None

    def get_all_events(self) -> List[Event]:
        """
        Retrieves all events from the database.
        Returns a list of SQLAlchemy Event objects.
        """
        return self.db.query(Event).all()

    def get_latest_events_by_title(self) -> Dict[str, Event]:
        """
        Returns a mapping of base_title -> latest Event (by start_date).
        The base_title is determined by splitting on ' - ' and taking the first part.
        """
        events = self.db.query(Event).order_by(Event.start_date).all()
        latest: Dict[str, Event] = {}
        for e in events:
            base_title = e.title.split(' - ')[0].strip()
            if base_title not in latest or e.start_date > latest[base_title].start_date:
                latest[base_title] = e
        return latest