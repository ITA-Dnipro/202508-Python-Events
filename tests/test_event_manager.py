import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from events_app.managers import EventManager
from events_app.models import Event
from dateutil.relativedelta import relativedelta 

@pytest.fixture
def manager():
    """
    Creates an EventManager instance with a mock database session.
    """
    mock_db = MagicMock()
    return EventManager(mock_db)

@pytest.fixture
def previous_event_mock():
    """
    Creates a mock object simulating an existing Event from the database.
    The start_date is set with timezone awareness (timezone.utc).
    """
    start_date = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    mock_event = MagicMock(spec=Event)
    mock_event.start_date = start_date
    mock_event.title = "Conference Base Title"
    
    return mock_event

def test_calculate_next_dates_monthly(manager, previous_event_mock):
    """
    Verifies that _calculate_next_dates correctly shifts dates by one month,
    sets the duration to 5 days, and the deadline 1 second before start.
    """
    expected_start_date = previous_event_mock.start_date + relativedelta(months=1)
    expected_end_date = expected_start_date + timedelta(days=5)
    expected_deadline = expected_start_date - timedelta(seconds=1)
    
    new_dates = manager._calculate_next_dates(previous_event_mock)
    
    assert new_dates['start_date'] == expected_start_date, \
        f"Expected start date {expected_start_date} but got {new_dates['start_date']}"
    
    assert new_dates['end_date'] == expected_end_date, \
        f"Expected end date {expected_end_date} but got {new_dates['end_date']}"
    
    assert new_dates['registration_deadline'] == expected_deadline, \
        f"Expected deadline {expected_deadline} but got {new_dates['registration_deadline']}"

def test_create_next_event_logic_and_title(manager, previous_event_mock):
    """
    Verifies that create_next_event correctly calculates dates, formats the title,
    and attempts to commit the new event to the database.
    """
    next_month_date = previous_event_mock.start_date + relativedelta(months=1)
    expected_month_year = next_month_date.strftime('%B %Y')
    expected_new_title = f"{previous_event_mock.title} - {expected_month_year}"
    
    mock_new_event = MagicMock()
    manager.db.refresh.return_value = mock_new_event
    result = manager.create_next_event(previous_event_mock)
    
    manager.db.add.assert_called_once()
    
    added_event = manager.db.add.call_args[0][0]
    assert added_event.title == expected_new_title
    assert added_event.start_date == next_month_date
    assert added_event.end_date == next_month_date + timedelta(days=5)
    
    manager.db.add.assert_called_once()
    manager.db.commit.assert_called_once()
    manager.db.refresh.assert_called_once()
    
    assert result == added_event, "Should return the newly created Event object"