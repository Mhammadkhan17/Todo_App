#!/usr/bin/env python3
"""
Tasks API Router

FastAPI router for task management endpoints.
Implements the 6 required RESTful endpoints for task operations.
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from src.models.task import Task, Priority, Status
from src.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskFilter,
    TaskListResponse, TaskCompletionToggle
)
from src.dependencies.auth import get_current_user
from src.database.session import get_session


router = APIRouter()


@router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    user_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session),
    status_filter: Optional[Status] = Query(None, description="Filter by task status"),
    priority: Optional[Priority] = Query(None, description="Filter by task priority"),
    due_date_from: Optional[date] = Query(None, description="Filter tasks due from this date"),
    due_date_to: Optional[date] = Query(None, description="Filter tasks due to this date"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """List tasks for a user with filtering and pagination."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these tasks"
        )

    # Build query
    query = session.query(Task).filter(Task.user_id == user_id)

    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter)

    if priority:
        query = query.filter(Task.priority == priority)

    if due_date_from:
        query = query.filter(Task.due_date >= due_date_from)

    if due_date_to:
        query = query.filter(Task.due_date <= due_date_to)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern)
            )
        )

    # Get total count for pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    tasks = query.offset(offset).limit(size).all()

    # Convert to response format
    task_responses = [TaskResponse.from_orm(task) for task in tasks]

    # Calculate pagination info
    total_pages = (total + size - 1) // size if total > 0 else 1

    return TaskListResponse(
        tasks=task_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.post("/{user_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    user_id: int,
    task_data: TaskCreate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new task for a user."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create tasks for this user"
        )

    # Create task
    task = Task(
        **task_data.dict(),
        user_id=user_id,
        status=Status.ACTIVE  # Default status
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


@router.get("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    user_id: int,
    task_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific task by ID."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this task"
        )

    # Get task
    task = session.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


@router.put("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    user_id: int,
    task_id: int,
    task_data: TaskUpdate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a specific task."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Get task
    task = session.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update task fields
    from datetime import datetime, timezone
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.now(timezone.utc)  # Update timestamp

    session.commit()
    session.refresh(task)

    return task


@router.delete("/{user_id}/tasks/{task_id}")
async def delete_task(
    user_id: int,
    task_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a task (soft delete by marking as completed and setting deleted flag)."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task"
        )

    # Get task
    task = session.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Soft delete by marking as completed
    # In a real application, you might want to add a 'deleted_at' field
    from datetime import datetime, timezone
    task.status = Status.COMPLETED
    task.updated_at = datetime.now(timezone.utc)
    task.completed_at = datetime.now(timezone.utc)

    session.commit()

    return {"message": "Task marked as completed (soft delete)"}


@router.patch("/{user_id}/tasks/{task_id}/complete", response_model=TaskCompletionToggle)
async def toggle_task_completion(
    user_id: int,
    task_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Toggle task completion status."""
    # Verify user authorization
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Get task
    task = session.query(Task).filter(
        Task.id == task_id,
        Task.user_id == user_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Toggle completion
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc)

    if task.status == Status.ACTIVE:
        task.status = Status.COMPLETED
        task.completed_at = current_time
        message = "Task marked as completed"
    else:
        task.status = Status.ACTIVE
        task.completed_at = None
        message = "Task marked as active"

    task.updated_at = current_time
    session.commit()
    session.refresh(task)

    return TaskCompletionToggle(
        id=task.id,
        status=task.status,
        completed_at=task.completed_at,
        message=message
    )