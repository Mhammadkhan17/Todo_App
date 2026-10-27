#!/usr/bin/env python3
"""Tasks API Router."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.dependencies.auth import get_current_user
from src.database.session import get_session
from src.models.task import Priority, Status
from src.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskCompletionToggle,
)
from src.services.task_service import TaskService


router = APIRouter()


def _authorize(current_user, user_id: int) -> None:
    if current_user.id != user_id and not hasattr(current_user, "is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access these tasks",
        )


@router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    user_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
    status_filter: Optional[Status] = Query(None, description="Filter by task status"),
    priority: Optional[Priority] = Query(None, description="Filter by task priority"),
    due_date_from: Optional[date] = Query(None, description="Filter tasks due from this date"),
    due_date_to: Optional[date] = Query(None, description="Filter tasks due to this date"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
):
    _authorize(current_user, user_id)

    tasks, total = TaskService.list(
        session,
        user_id=user_id,
        status=status_filter,
        priority=priority,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        page=page,
        size=size,
    )

    total_pages = (total + size - 1) // size if total > 0 else 1
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post("/{user_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    user_id: int,
    task_data: TaskCreate,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _authorize(current_user, user_id)
    return TaskService.create(
        session,
        user_id=user_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
    )


@router.get("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    user_id: int,
    task_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _authorize(current_user, user_id)
    return TaskService.get(session, user_id=user_id, task_id=task_id)


@router.put("/{user_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    user_id: int,
    task_id: int,
    task_data: TaskUpdate,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _authorize(current_user, user_id)
    return TaskService.update(
        session,
        user_id=user_id,
        task_id=task_id,
        changes=task_data.model_dump(exclude_unset=True),
    )


@router.delete("/{user_id}/tasks/{task_id}")
async def delete_task(
    user_id: int,
    task_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _authorize(current_user, user_id)
    TaskService.soft_delete(session, user_id=user_id, task_id=task_id)
    return {"message": "Task marked as completed (soft delete)"}


@router.patch("/{user_id}/tasks/{task_id}/complete", response_model=TaskCompletionToggle)
async def toggle_task_completion(
    user_id: int,
    task_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _authorize(current_user, user_id)
    task = TaskService.toggle_completed(session, user_id=user_id, task_id=task_id)
    message = (
        "Task marked as completed"
        if task.status == Status.COMPLETED
        else "Task marked as active"
    )
    return TaskCompletionToggle(
        id=task.id,
        status=task.status,
        completed_at=task.completed_at,
        message=message,
    )
