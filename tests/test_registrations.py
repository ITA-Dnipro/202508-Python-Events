import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta, timezone
from events_app.main import app
from events_app.database import Base, get_db
from events_app.models import Event, EventRegistration
from events_app.dependencies import get_current_user, CurrentUser

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def session():
    """Creates a new clean database session for each test."""
    Base.metadata.create_all(bind=engine) 
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) 

@pytest.fixture()
def client(session):
    """Creates a test client using the test database session."""
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

def create_active_event(db):
    """Creates an active event scheduled for the future."""
    event = Event(
        title="Future Tech",
        theme="IT",
        description="Cool event",
        start_date=datetime.now(timezone.utc) + timedelta(days=5),
        end_date=datetime.now(timezone.utc) + timedelta(days=6),
        registration_deadline=datetime.now(timezone.utc) + timedelta(days=2),
        is_active=True
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def mock_user(user_id=1, role="startup"):
    """Simulates an authenticated user."""
    return CurrentUser(id=user_id, allowed_roles=[role], role=role)

def test_register_success_201(client, session):
    """Tests successful registration scenario returning status 201."""
    event = create_active_event(session)

    app.dependency_overrides[get_current_user] = lambda: mock_user(1, "startup")

    response = client.post(
        f"/events/{event.id}/register",
        json={"role": "startup"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == 1
    assert data["status"] == "registered"
    
    del app.dependency_overrides[get_current_user]

def test_registration_closed_400(client, session):
    """Tests registration attempt after deadline returning status 400."""
    event = Event(
        title="Past Deadline",
        theme="IT",
        start_date=datetime.now(timezone.utc) + timedelta(days=5),
        end_date=datetime.now(timezone.utc) + timedelta(days=6),
        registration_deadline=datetime.now(timezone.utc) - timedelta(days=1), 
        is_active=True
    )
    session.add(event)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user(1, "investor")

    response = client.post(
        f"/events/{event.id}/register",
        json={"role": "investor"}
    )

    assert response.status_code == 400
    
    del app.dependency_overrides[get_current_user]

def test_duplicate_prevention_409(client, session):
    """Tests prevention of duplicate registrations returning status 409."""
    event = create_active_event(session)
    app.dependency_overrides[get_current_user] = lambda: mock_user(user_id=10, role="startup")

    client.post(f"/events/{event.id}/register", json={"role": "startup"})

    response = client.post(f"/events/{event.id}/register", json={"role": "startup"})

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]

    del app.dependency_overrides[get_current_user]

def test_cancel_registration_204(client, session):
    """Tests successful cancellation of registration returning status 204."""
    event = create_active_event(session)
    user_id = 77
    
    reg = EventRegistration(
        event_id=event.id,
        user_id=user_id,
        role="startup",
        status="registered"
    )
    session.add(reg)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user(user_id, "startup")

    response = client.delete(f"/events/{event.id}/register")

    assert response.status_code == 204
    
    assert session.query(EventRegistration).filter_by(user_id=user_id).first() is None

    del app.dependency_overrides[get_current_user]

def test_unauthorized_request_401(client, session):
    """Tests unauthorized registration attempt returning status 401."""
    event = create_active_event(session)

    app.dependency_overrides.pop(get_current_user, None)

    response = client.post(
        f"/events/{event.id}/register",
        json={"role": "startup"}
    )

    assert response.status_code == 401