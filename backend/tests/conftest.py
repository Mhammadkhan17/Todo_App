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
from sqlalchemy.orm import sessionmaker

from main import app
from src.database.engine import database_engine
from src.database.session import get_session
from src.models import User, Task


# Create test database
@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # Use in-memory SQLite for tests
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

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
        try:
            session = sessionmaker(autocommit=False, autoflush=False, bind=test_db)()
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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