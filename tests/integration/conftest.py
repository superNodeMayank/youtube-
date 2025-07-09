from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session as SQLModelSession
from fastapi.testclient import TestClient
import pytest

from src.main import app
from src.database import get_session
from src.models import User
from src.config import settings
from src.auth import get_password_hash


TESTING_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TESTING_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function")
def db_session_override():
    """Fixture to handle DB session override and table creation/cleanup."""
    # Create tables before the session is used by the app
    SQLModel.metadata.create_all(bind=test_engine)

    def _override_get_session():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session

    yield # This is where the test runs

    # Clean up: drop tables and clear overrides
    SQLModel.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(db_session_override):
    """
    Pytest fixture to provide a TestClient instance.
    Relies on db_session_override to manage DB state and dependency overrides.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session(db_session_override):
    """
    Fixture to get a direct session to the test DB, primarily for setting up test data.
    Ensures that it uses the same overridden session mechanism.
    """
    # The db_session_override fixture already handles setting up and tearing down the database environment.
    # We just need a session instance from TestingSessionLocal.
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Helper to create a user directly in the DB for testing
def create_test_user(
    session: SQLModelSession,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword",
    ai_global_toggle: bool = False
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        ai_assist_enabled_global=ai_global_toggle
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# Helper to get auth headers
def get_auth_headers_for_user(
    test_client: TestClient,
    username: str,
    password: str # Plain password
) -> dict:
    login_data = {"username": username, "password": password}
    # Ensure the TestClient uses the overridden app state
    response = test_client.post("/token", data=login_data)

    if response.status_code != 200:
        print(f"Login failed for {username} during test setup: {response.status_code} - {response.text}")
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
