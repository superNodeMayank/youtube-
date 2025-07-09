from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session as SQLModelSession # Use SQLModel's Session for SQLModel operations
from fastapi.testclient import TestClient
import pytest # Using pytest for fixtures and cleaner test structure

from src.main import app # Main FastAPI app
from src.database import get_session # Original get_session dependency
from src.models import User # For creating test users if needed
from src.config import settings # For JWT settings if needed for manual token creation in tests

# --- Test Database Setup ---
# Use a separate in-memory SQLite database for testing
TESTING_DATABASE_URL = "sqlite:///:memory:" # In-memory SQLite

# Create a new SQLAlchemy engine for the test database
# connect_args={"check_same_thread": False} is needed only for SQLite if used in a multi-threaded context.
# TestClient runs in a single thread, but good practice.
test_engine = create_engine(TESTING_DATABASE_URL, connect_args={"check_same_thread": False})

# Create a sessionmaker for the test database
# Use autoflush=False and autocommit=False for testing, giving more control
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# --- Dependency Override for Database Session ---
def override_get_session():
    """
    Overrides the get_session dependency to use the test database.
    Creates tables for each test session and drops them afterwards if needed,
    or relies on in-memory DB being fresh.
    For in-memory, the DB is fresh each time the engine is made or tables are created.
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# --- Pytest Fixture for Test Client and Database Setup ---
@pytest.fixture(scope="function") # "function" scope means it runs for each test function
def client():
    """
    Pytest fixture to provide a TestClient instance with a clean in-memory database
    for each test function.
    """
    # Apply the dependency override for the database session
    app.dependency_overrides[get_session] = override_get_session

    # Create all tables in the (fresh) in-memory database before tests run
    SQLModel.metadata.create_all(bind=test_engine)

    with TestClient(app) as test_client:
        yield test_client # Provide the test client to the test function

    # Drop all tables after tests run to ensure clean state for next test if engine was persistent
    # For :memory:, this is not strictly necessary as it's wiped when connection closes,
    # but good practice if switching to a file-based test DB.
    SQLModel.metadata.drop_all(bind=test_engine)

    # Clear dependency overrides after tests
    app.dependency_overrides.clear()


# --- Helper Functions for Tests (Optional) ---
def create_user_in_db(db_session: SQLModelSession, user_data: dict) -> User:
    """
    Helper to directly create a user in the test DB.
    `user_data` should include 'username', 'email', 'password_hash'.
    """
    from src.auth import get_password_hash # Local import to avoid circular issues at module level

    db_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=get_password_hash(user_data["password"]) # Hash the password
    )
    if "ai_assist_enabled_global" in user_data:
        db_user.ai_assist_enabled_global = user_data["ai_assist_enabled_global"]

    db_session.add(db_user)
    db_session.commit()
    db_session.refresh(db_user)
    return db_user

def get_auth_headers(client: TestClient, username: str, password: str) -> dict:
    """
    Helper to log in a user and return authentication headers.
    """
    login_data = {"username": username, "password": password}
    response = client.post("/token", data=login_data) # FastAPI TestClient handles form data correctly
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        # print(f"Login failed for {username}: {response.status_code} {response.text}")
        raise Exception(f"Login failed for user {username} with status {response.status_code}. Response: {response.text}")


# Note: If using unittest.TestCase, you would typically handle setup and teardown
# in setUp, tearDown, setUpClass, tearDownClass methods.
# Pytest fixtures are generally more flexible and preferred for FastAPI testing.
# I will proceed assuming tests will be written in pytest style.
# If I need to use unittest style, I will adapt.

# Ensure this file is in `tests/` or `tests/integration/` and accessible.
# Pytest will automatically discover fixtures in conftest.py files.
# If this is test_utils.py, fixtures need to be imported or defined in conftest.py
# For simplicity, I will assume this content will be in `tests/integration/conftest.py`
# or that tests explicitly import `client` fixture from `tests.test_utils`.
# I will rename this file to `conftest.py` conceptually for now.
