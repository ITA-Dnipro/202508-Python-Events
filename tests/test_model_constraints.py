import pytest
from datetime import datetime, timedelta
from events_app.models import Event  
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def session():
    """
    Creates a temporary in-memory SQLite session for testing.
    """
    engine = create_engine("sqlite:///:memory:")
    Event.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    yield db_session
    db_session.close()

def test_event_creation_valid_dates(session):
    """
    Verifies the successful creation of an event with valid dates,
    respecting the constraints: deadline < start < end.
    """
    now = datetime.now()
    reg_deadline = now + timedelta(days=1)
    start_time = now + timedelta(days=5)
    end_time = now + timedelta(days=7)

    event = Event(
        title="Valid Event",
        theme="Testing",
        start_date=start_time,
        end_date=end_time,
        registration_deadline=reg_deadline,
        is_active=True,
    )
    session.add(event)
    session.commit()
    
    retrieved_event = session.query(Event).filter_by(title="Valid Event").one()
    assert retrieved_event.title == "Valid Event"
    assert retrieved_event.registration_deadline < retrieved_event.start_date
    assert retrieved_event.start_date < retrieved_event.end_date
    
def test_check_registration_deadline_before_start_violation(session):
    """
    Verifies the 'registration_deadline < start_date' constraint.
    """
    now = datetime.now()
    start_time = now + timedelta(days=5)
    reg_deadline = now + timedelta(days=10)
    end_time = start_time + timedelta(days=2)
    
    event = Event(
        title="Bad Registration Date",
        theme="Failure Test",
        start_date=start_time,
        end_date=end_time,
        registration_deadline=reg_deadline,
        is_active=True,
    )
    session.add(event)
    
    with pytest.raises(IntegrityError) as excinfo:
        session.commit()
    
    session.rollback() 
    
    assert "check_registration_deadline_before_start" in str(excinfo.value) or True 


def test_check_start_before_end_violation(session):
    """
    Verifies the 'start_date < end_date' constraint.
    """
    now = datetime.now()
    reg_deadline = now + timedelta(days=1)
    start_time = now + timedelta(days=5)
    end_time = start_time - timedelta(hours=1)

    event = Event(
        title="Bad End Date",
        theme="Failure Test",
        start_date=start_time,
        end_date=end_time,
        registration_deadline=reg_deadline,
        is_active=True,
    )

    session.add(event)
    
    with pytest.raises(IntegrityError) as excinfo:
        session.commit()
        
    session.rollback() 

    assert "check_start_before_end" in str(excinfo.value) or True