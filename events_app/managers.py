from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta
from .models import Event 

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
            new_start_date = previous_event.start_date + date_shift
            duration = timedelta(days=5) 
            new_end_date = new_start_date + duration
            new_registration_deadline = new_start_date
            
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
        new_event_description = "will be generated based on theme of new_event_theme"
        
        new_event = Event(
            title=new_event_title,
            theme=new_event_theme,
            description=new_event_description,

            start_date=new_dates['start_date'],
            end_date=new_dates['end_date'],
            registration_deadline=new_dates['registration_deadline'],
            is_active=True,
        )
        self.db.add(new_event)
        
        return new_event