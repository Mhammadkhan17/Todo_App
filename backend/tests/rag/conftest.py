"""Shared fixtures for RAG tests: DB tables, in-memory Qdrant, auth helpers."""

import pytest
from qdrant_client import QdrantClient
from sqlmodel import Session, SQLModel

import src.models.rag  # noqa: F401  register Document/ChatSession/ChatMessage on SQLModel.metadata
from src.auth.jwt_service import JWTService
from src.models.rag import ChatMessage, ChatSession, Document
from src.rag.store import reset_singletons


@pytest.fixture(scope="session", autouse=True)
def _rag_tables(test_db):
    SQLModel.metadata.create_all(bind=test_db)


@pytest.fixture(autouse=True)
def _clear_rag_rows(test_db):
    # session-scoped DB is shared across files; each test starts with no
    # Document/ChatSession/ChatMessage rows (users are kept for auth reuse)
    with test_db.begin() as conn:
        for model in (ChatMessage, ChatSession, Document):
            conn.execute(model.__table__.delete())


@pytest.fixture(autouse=True)
def _reset_store_singletons():
    reset_singletons()
    yield
    reset_singletons()


@pytest.fixture
def qdrant_client():
    return QdrantClient(":memory:")


@pytest.fixture
def db_session(test_db):
    # sqlmodel.Session (adds .exec); plain sqlalchemy sessionmaker lacks it
    session = Session(bind=test_db)
    yield session
    session.close()


_REGISTERED: dict[str, dict] = {}


def _register(
    client, *, username, email, password="testpassword123", full_name="Test User"
):
    # register once per session; later tests reuse the cached row (the
    # session-scoped DB would 409 a duplicate email)
    if username in _REGISTERED:
        return _REGISTERED[username]
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
    user = response.json()
    _REGISTERED[username] = user
    return user


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
    # unique creds so we never collide with tests/test_auth.py's sample user
    return make_user("raguser", "rag@example.com")


@pytest.fixture
def other_user_headers(make_user):
    return make_user("ragother", "rag-other@example.com")
