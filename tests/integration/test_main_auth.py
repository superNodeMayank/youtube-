import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as SQLModelSession # For type hinting if using db_session directly

from src.schemas import UserRead
from tests.integration.conftest import create_test_user # Helper to create user in DB

# Tests are written in pytest style, using the `client` fixture from conftest.py

def test_register_user_success(client: TestClient):
    response = client.post(
        "/users/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "ai_assist_enabled_global": False, # Optional, will use default if not provided
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert "user_id" in data
    assert "password_hash" not in data # Ensure password hash is not returned

def test_register_user_duplicate_username(client: TestClient, db_session: SQLModelSession):
    # Create a user directly in the DB first
    create_test_user(db_session, username="existinguser", email="unique_email@example.com", password="password")

    response = client.post(
        "/users/register",
        json={
            "username": "existinguser", # Duplicate username
            "email": "another_email@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400 # Expect Bad Request
    assert "Username already registered" in response.json()["detail"]

def test_register_user_duplicate_email(client: TestClient, db_session: SQLModelSession):
    create_test_user(db_session, username="unique_user", email="existing@example.com", password="password")

    response = client.post(
        "/users/register",
        json={
            "username": "another_user",
            "email": "existing@example.com", # Duplicate email
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_for_access_token_success(client: TestClient, db_session: SQLModelSession):
    # 1. Create a user first (either via API or directly in DB for test setup)
    create_test_user(db_session, username="loginuser", email="login@example.com", password="loginpassword")

    # 2. Attempt to login
    login_data = {"username": "loginuser", "password": "loginpassword"}
    response = client.post("/token", data=login_data) # Form data for OAuth2PasswordRequestForm

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_for_access_token_wrong_username(client: TestClient):
    login_data = {"username": "nonexistentuser", "password": "password"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 401 # Unauthorized
    assert "Incorrect username or password" in response.json()["detail"]

def test_login_for_access_token_wrong_password(client: TestClient, db_session: SQLModelSession):
    create_test_user(db_session, username="authuser", email="auth@example.com", password="correctpassword")

    login_data = {"username": "authuser", "password": "wrongpassword"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_read_users_me_success(client: TestClient, db_session: SQLModelSession):
    # 1. Create user and get token
    test_username = "me_user"
    test_password = "me_password"
    created_user = create_test_user(db_session, username=test_username, email="me@example.com", password=test_password)

    login_response = client.post("/token", data={"username": test_username, "password": test_password})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Request /users/me
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Validate against the UserRead schema (which is what User model becomes via model_validate)
    # Pydantic models can be used for response validation if needed, but here direct assertion.
    assert data["username"] == created_user.username
    assert data["email"] == created_user.email
    assert data["user_id"] == created_user.user_id
    assert data["ai_assist_enabled_global"] == created_user.ai_assist_enabled_global


def test_read_users_me_unauthenticated(client: TestClient):
    response = client.get("/users/me") # No auth header
    assert response.status_code == 401 # Expect Unauthorized
    assert "Not authenticated" in response.json()["detail"] # Or "Could not validate credentials"

# To run these tests:
# Ensure pytest is installed (pip install pytest)
# From the project root, run: pytest tests/integration/test_main_auth.py
# Or simply: pytest (if tests directory is configured or named 'tests')
