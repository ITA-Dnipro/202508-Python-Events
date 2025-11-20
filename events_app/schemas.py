from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone, date

class EventBase(BaseModel):
    '''Base model for event data. Contains logic for status calculation.'''
    title : str
    theme : str
    description : Optional[str] = ""
    start_date : date
    end_date : date
    registration_deadline : date
    
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
        orm_mode = True 

class EventCreate(EventBase):
    '''Model used for creating new events via the API. Excludes DB-generated fields.'''
    is_active : bool = True

class EventSerializer(EventBase):
    '''Serializer model for event data get from the database, including status.'''
    id : int
    is_active : bool
    created_at : datetime