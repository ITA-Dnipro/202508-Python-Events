import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from events_app.tasks import generate_recurring_events

@pytest.fixture
def mock_event_data():
    """
    Creates a mock object simulating an existing, outdated event from the DB.
    The start_date is set in the past to ensure the generation condition (now > latest_db_date) is met.
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    latest_db_date = now - timedelta(days=30)
    
    mock_event = MagicMock()
    mock_event.title = "Conference Base Title - Previous Month 2025"
    mock_event.theme = "Technology"
    mock_event.start_date = latest_db_date
    mock_event.id = 1
    
    return mock_event

@pytest.fixture
def new_dates_data(mock_event_data):
    """
    Creates mock calculated dates, simulating the output of EventManager._calculate_next_dates.
    """
    new_start_date = mock_event_data.start_date + timedelta(days=30)
    return {
        'start_date': new_start_date,
        'end_date': new_start_date + timedelta(days=2),
        'registration_deadline': new_start_date - timedelta(days=5)
    }

@patch('events_app.tasks.SessionLocal')
@patch('events_app.tasks.EventManager')
@patch('events_app.tasks.datetime')
def test_generate_recurring_events_success(mock_dt, MockEventManager, MockSessionLocal, 
                                          mock_event_data, new_dates_data):
    """
    Verifies successful generation when the base event is outdated and the next event does not exist.
    Checks if EventManager methods are called and transaction is committed.
    """
    current_mock_time = datetime.now(timezone.utc).replace(microsecond=0)
    mock_dt.now.return_value = current_mock_time
    mock_dt.now.side_effect = lambda tz=None: current_mock_time.astimezone(tz) if tz else current_mock_time

    mock_db = MockSessionLocal.return_value
    mock_manager = MockEventManager.return_value

    base_title = "Conference Base Title"
    mock_manager.get_latest_events_by_title.return_value = {base_title: mock_event_data}
    mock_manager._calculate_next_dates.return_value = new_dates_data
    mock_db.query.return_value.filter.return_value.first.return_value = None

    new_event_mock = MagicMock(title=f"{base_title} - {new_dates_data['start_date'].strftime('%B %Y')}")
    mock_manager.create_next_event.return_value = new_event_mock
    
    result = generate_recurring_events()

    mock_manager._calculate_next_dates.assert_called_once_with(mock_event_data)
    mock_manager.create_next_event.assert_called_once_with(mock_event_data)
    mock_db.commit.assert_called_once()
    assert result['created_count'] == 1
    mock_db.close.assert_called_once()


@patch('events_app.tasks.SessionLocal')
@patch('events_app.tasks.EventManager')
@patch('events_app.tasks.datetime')
def test_generate_recurring_events_skip_exists(mock_dt, MockEventManager, MockSessionLocal, 
                                              mock_event_data, new_dates_data):
    """
    Verifies that the task skips generation if the next event already exists in the DB.
    Checks that create_next_event and db.commit are not called.
    """
    current_mock_time = datetime.now(timezone.utc).replace(microsecond=0)
    mock_dt.now.return_value = current_mock_time
    mock_dt.now.side_effect = lambda tz=None: current_mock_time.astimezone(tz) if tz else current_mock_time

    mock_db = MockSessionLocal.return_value
    mock_manager = MockEventManager.return_value

    base_title = "Conference Base Title"
    mock_manager.get_latest_events_by_title.return_value = {base_title: mock_event_data}
    mock_manager._calculate_next_dates.return_value = new_dates_data
    
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    result = generate_recurring_events()

    mock_manager.create_next_event.assert_not_called()
    mock_db.commit.assert_not_called()
    assert result['created_count'] == 0
    mock_db.close.assert_called_once()


@patch('events_app.tasks.SessionLocal')
@patch('events_app.tasks.EventManager')
def test_generate_recurring_events_handles_exception(MockEventManager, MockSessionLocal, mock_event_data):
    """
    Verifies that the task handles exceptions by rolling back the transaction and closing the DB session.
    """
    mock_db = MockSessionLocal.return_value
    mock_manager = MockEventManager.return_value
    
    mock_manager.get_latest_events_by_title.side_effect = Exception("DB connection error")

    with pytest.raises(Exception, match="DB connection error"):
        generate_recurring_events()

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()