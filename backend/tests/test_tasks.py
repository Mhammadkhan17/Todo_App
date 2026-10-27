#!/usr/bin/env python3
"""
Test task endpoints

Tests for task CRUD operations and filtering.
"""

from fastapi.testclient import TestClient


def test_create_task(client: TestClient, sample_user_data: dict, sample_task_data: dict):
    """Test creating a new task."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]

    # Create task
    response = client.post(
        f"/api/{user_id}/tasks",
        json=sample_task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_task_data["title"]
    assert data["description"] == sample_task_data["description"]
    assert data["priority"] == sample_task_data["priority"]
    assert data["status"] == "ACTIVE"
    assert data["user_id"] == user_id


def test_list_tasks(client: TestClient, sample_user_data: dict, sample_task_data: dict):
    """Test listing tasks for a user."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]

    # Create a task first
    client.post(
        f"/api/{user_id}/tasks",
        json=sample_task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    # List tasks
    response = client.get(
        f"/api/{user_id}/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "total" in data
    assert data["total"] == 1
    assert len(data["tasks"]) == 1


def test_get_task(client: TestClient, sample_user_data: dict, sample_task_data: dict):
    """Test getting a specific task."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]

    # Create a task first
    create_response = client.post(
        f"/api/{user_id}/tasks",
        json=sample_task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    task_id = create_response.json()["id"]

    # Get task
    response = client.get(
        f"/api/{user_id}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == sample_task_data["title"]


def test_update_task(client: TestClient, sample_user_data: dict, sample_task_data: dict):
    """Test updating a task."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]

    # Create a task first
    create_response = client.post(
        f"/api/{user_id}/tasks",
        json=sample_task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    task_id = create_response.json()["id"]

    # Update task
    update_data = {
        "title": "Updated Task Title",
        "description": "Updated description",
        "priority": "HIGH"
    }

    response = client.put(
        f"/api/{user_id}/tasks/{task_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
    assert data["priority"] == update_data["priority"]


def test_toggle_task_completion(client: TestClient, sample_user_data: dict, sample_task_data: dict):
    """Test toggling task completion status."""
    # Register and login user
    client.post("/api/register", json=sample_user_data)

    login_response = client.post("/api/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user_id"]

    # Create a task first
    create_response = client.post(
        f"/api/{user_id}/tasks",
        json=sample_task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    task_id = create_response.json()["id"]

    # Toggle completion
    response = client.patch(
        f"/api/{user_id}/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["status"] == "COMPLETED"
    assert "message" in data


def test_delete_task_is_soft_delete(client, sample_user_data, sample_task_data):
    client.post("/api/register", json=sample_user_data)
    login = client.post(
        "/api/token",
        json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"],
        },
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    created = client.post(
        f"/api/{login['user_id']}/tasks",
        json=sample_task_data,
        headers=headers,
    ).json()

    response = client.delete(
        f"/api/{login['user_id']}/tasks/{created['id']}",
        headers=headers,
    )
    assert response.status_code == 200

    fetched = client.get(
        f"/api/{login['user_id']}/tasks/{created['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "COMPLETED"