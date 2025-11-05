from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

class EventBase(BaseModel):
    '''Base model for event data.'''
    id : Optional[int]
    title : str
    theme : str
    description : Optional[str] = ""
    start_date : datetime
    end_date : datetime
    registration_deadline : datetime
    is_active : bool
    created_at : Optional[datetime]
    
    @property
    def status(self) -> str:
        '''Determines the current status of the event based on the current date.'''
        now = datetime.now(timezone.utc)
        if now > self.end_date:
            return "Completed"
        elif now > self.registration_deadline:
            return "Closed"
        return "Open"

    class Config:
        from_attributes = True

class EventSerializer(EventBase):
    '''Serializer model for event data with status.'''
    status: str 

