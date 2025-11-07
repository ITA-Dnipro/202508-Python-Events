from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

class EventBase(BaseModel):
    '''Base model for event data. Contains logic for status calculation.'''
    id : Optional[int] = None
    title : str
    theme : str
    description : Optional[str] = ""
    start_date : datetime
    end_date : datetime
    registration_deadline : datetime
    is_active : bool
    created_at : Optional[datetime] = None
    
    @property
    def event_status(self) -> str:
        '''Determines the current status of the event based on the current date.'''
        now = datetime.now(timezone.utc)
        if now > self.end_date:
            return "Completed"
        elif now > self.registration_deadline:
            return "Closed"
        return "Open"

    class Config:
        orm_mode = True 

class EventCreate(BaseModel):
    '''Model used for creating new events via the API.'''
    title : str
    theme : str
    description : Optional[str] = ""
    start_date : datetime
    end_date : datetime
    registration_deadline : datetime
    is_active : bool = True
    
    class Config:
        orm_mode = True

class EventSerializer(BaseModel):
    '''Serializer model for event data with status. Defined explicitly to avoid inheritance conflicts.'''
    id : Optional[int] = None
    title : str
    theme : str
    description : Optional[str] = ""
    start_date : datetime
    end_date : datetime
    registration_deadline : datetime
    is_active : bool
    created_at : Optional[datetime] = None

    @property
    def event_status(self) -> str:
        '''Calculates the current status of the event based on the current date.'''
        now = datetime.now(timezone.utc)
        if now > self.end_date:
            return "Completed"
        elif now > self.registration_deadline:
            return "Closed"
        return "Open"
            
    class Config:
        orm_mode = True