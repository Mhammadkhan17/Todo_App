#!/usr/bin/env python3
"""
Test configuration and fixtures

Shared test configuration and fixtures for the test suite.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session

from main import app
from src.database.engine import database_engine
from src.database.session import get_session
from src.models import User, Task


def _allow_testclient_host() -> None:
    """Dev TrustedHostMiddleware rejects TestClient's 'testserver' host."""
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    for middleware in app.user_middleware:
        if getattr(middleware, "cls", None) is TrustedHostMiddleware:
            options = getattr(middleware, "kwargs", None) or getattr(middleware, "options", None)
            if options is not None:
                options["allowed_hosts"] = ["testserver", "localhost", "127.0.0.1", "0.0.0.0"]


_allow_testclient_host()


# Create test database
@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # SingletonThreadPool gives each thread its own empty :memory: DB;
    # StaticPool shares one connection so the app thread sees the same tables.
    test_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    User.metadata.create_all(bind=test_engine)
    Task.metadata.create_all(bind=test_engine)

    yield test_engine

    # Cleanup
    User.metadata.drop_all(bind=test_engine)
    Task.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    def override_get_session():
        # sqlmodel.Session (adds .exec) — routes call db.exec(...)
        try:
            session = Session(bind=test_db)
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clean_tasks(test_db):
    """Each test starts with no task rows (the shared user rows persist)."""
    with test_db.begin() as conn:
        conn.execute(Task.__table__.delete())
    yield


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "MEDIUM",
        "status": "ACTIVE"
    }