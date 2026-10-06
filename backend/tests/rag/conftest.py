"""Shared fixtures for RAG tests: DB tables, in-memory Qdrant, auth helpers."""

import pytest
from qdrant_client import QdrantClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

import src.models.rag  # noqa: F401  register Document/ChatSession/ChatMessage on SQLModel.metadata
from src.auth.jwt_service import JWTService


@pytest.fixture(scope="session", autouse=True)
def _rag_tables(test_db):
    SQLModel.metadata.create_all(bind=test_db)


@pytest.fixture
def qdrant_client():
    return QdrantClient(":memory:")


@pytest.fixture
def db_session(test_db):
    session = sessionmaker(autocommit=False, autoflush=False, bind=test_db)()
    yield session
    session.close()


def _register(
    client, *, username, email, password="testpassword123", full_name="Test User"
):
    response = client.post(
        "/api/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _bearer(user: dict) -> dict:
    # /api/token goes through AuthService.authenticate_user, which uses the real
    # engine (test-override bypass) — mint the token directly instead.
    token = JWTService.create_access_token(
        {"sub": user["username"], "user_id": user["id"], "email": user["email"]}
    )["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(client):
    def _make(username: str, email: str) -> dict:
        return _bearer(_register(client, username=username, email=email))

    return _make


@pytest.fixture
def auth_headers(make_user):
    return make_user("testuser", "test@example.com")


@pytest.fixture
def other_user_headers(make_user):
    return make_user("otheruser", "other@example.com")
