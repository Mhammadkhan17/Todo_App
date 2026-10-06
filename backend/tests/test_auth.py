#!/usr/bin/env python3
"""
Test authentication endpoints

Tests for user registration, login, and authentication functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_register_user(client: TestClient, sample_user_data: dict):
    """Test user registration."""
    response = client.post("/api/register", json=sample_user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == sample_user_data["email"]
    assert data["username"] == sample_user_data["username"]
    assert data["full_name"] == sample_user_data["full_name"]


def test_register_user_duplicate_email(client: TestClient, sample_user_data: dict):
    """Test registration with duplicate email."""
    # Register user first time
    client.post("/api/register", json=sample_user_data)

    # Try to register with same email
    duplicate_data = sample_user_data.copy()
    duplicate_data["username"] = "differentuser"
    duplicate_data["password"] = "differentpassword"

    response = client.post("/api/register", json=duplicate_data)
    assert response.status_code == 400


def test_login_user(client: TestClient, sample_user_data: dict):
    """Test user login."""
    # Register user first
    client.post("/api/register", json=sample_user_data)

    # Login
    login_data = {
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    }

    response = client.post("/api/token", json=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == 1  # First user should have ID 1


def test_login_invalid_credentials(client: TestClient, sample_user_data: dict):
    """Test login with invalid credentials."""
    # Register user first
    client.post("/api/register", json=sample_user_data)

    # Try login with wrong password
    login_data = {
        "username": sample_user_data["username"],
        "password": "wrongpassword"
    }

    response = client.post("/api/token", json=login_data)
    assert response.status_code == 401


def test_get_current_user_info(client: TestClient, sample_user_data: dict):
    """Test getting current user info."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]

    # Get user info
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == sample_user_data["username"]
    assert data["email"] == sample_user_data["email"]