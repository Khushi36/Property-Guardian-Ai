"""
Tests for the Property Guardian AI FastAPI application.
Uses FastAPI TestClient with a test database override.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from main import app as main_app

# --- Test Database Setup ---
# Use SQLite in-memory for fast tests (no Postgres dependency)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
main_app.dependency_overrides[get_db] = override_get_db

client = TestClient(main_app)


# --- Fixtures ---
@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# --- Health Check Tests ---
def test_health_check():
    """GET /health should return status 'active'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "PostgreSQL" in data["components"]


# --- Registration Tests ---
def test_register_user():
    """POST /api/v1/users/ should create a new user."""
    response = client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True


def test_register_duplicate_user():
    """Registering with the same email should return 400."""
    payload = {"email": "dupe@example.com", "password": "password123"}
    client.post("/api/v1/users/", json=payload)
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


# --- Login Tests ---
def test_login_success():
    """Login with correct credentials should return a JWT token."""
    client.post(
        "/api/v1/users/", json={"email": "login@example.com", "password": "pass123"}
    )
    response = client.post(
        "/api/v1/token", data={"username": "login@example.com", "password": "pass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    """Login with wrong password should return 401."""
    client.post(
        "/api/v1/users/", json={"email": "wrong@example.com", "password": "correct"}
    )
    response = client.post(
        "/api/v1/token", data={"username": "wrong@example.com", "password": "incorrect"}
    )
    assert response.status_code == 401


def test_login_nonexistent_user():
    """Login with non-existent user should return 401."""
    response = client.post(
        "/api/v1/token", data={"username": "ghost@example.com", "password": "anything"}
    )
    assert response.status_code == 401


# --- Protected Endpoint Tests ---
def test_protected_endpoint_without_token():
    """Accessing fraud-check without auth should return 401."""
    response = client.get("/api/v1/fraud-check")
    assert response.status_code == 401


def test_protected_endpoint_with_token():
    """Accessing fraud-check with valid token should succeed."""
    # Register + Login
    client.post(
        "/api/v1/users/", json={"email": "auth@example.com", "password": "pass123"}
    )
    login_resp = client.post(
        "/api/v1/token", data={"username": "auth@example.com", "password": "pass123"}
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/fraud-check", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


# --- Direct SQL Endpoint Removed ---
def test_direct_sql_requires_auth():
    """Verify /query/direct_sql requires authentication."""
    response = client.post("/api/v1/query/direct_sql", json={"query": "SELECT 1"})
    assert response.status_code == 401  # Requires auth

