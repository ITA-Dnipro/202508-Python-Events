from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func, CheckConstraint
from .database import Base

class Event(Base):
    '''SQLAlchemy model for the event table.'''
    __tablename__ = "event"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    theme = Column(String(100), nullable=False)
    description = Column(Text, default="")
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    registration_deadline = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(registration_deadline < start_date, name="check_registration_deadline_before_start"),
        CheckConstraint(start_date < end_date, name="check_start_before_end"),
    )
