from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base
import enum

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
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(registration_deadline < start_date, name="check_registration_deadline_before_start"),
        CheckConstraint(start_date < end_date, name="check_start_before_end"),
    )

class RegistrationStatus(str, enum.Enum):
    registered = "registered"
    cancelled = "cancelled"

class EventRegistration(Base):
    '''SQLAlchemy model for event registrations.'''
    __tablename__ = "event_registration"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    status = Column(String(20), default=RegistrationStatus.registered.value) 
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    event = relationship("Event", back_populates="registrations")

    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='uq_event_user_registration'),
    )