#!/usr/bin/env python3
"""
Users API Router

FastAPI router for user management endpoints.
"""

from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.user import UserResponse, UserUpdate
from src.dependencies.auth import get_current_user, require_admin
from src.database.session import get_session


router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user by ID."""
    # Users can only view their own profile, or admins can view any profile
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update user information."""
    # Users can only update their own profile, or admins can update any profile
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = user.updated_at  # Update timestamp

    session.commit()
    session.refresh(user)

    return user


@router.get("/{user_id}/profile", response_model=UserResponse)
async def get_user_profile(
    user_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user profile (same as get_user, but more explicit)."""
    return await get_user(user_id, current_user, session)


@router.get("/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user statistics."""
    # Users can only view their own stats, or admins can view any stats
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these stats"
        )

    from sqlalchemy import func
    from src.models.task import Task, Status
    from datetime import date

    # Get task statistics
    total_tasks = session.query(func.count(Task.id)).filter(Task.user_id == user_id).scalar()
    active_tasks = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.ACTIVE
    ).scalar()
    completed_tasks = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.COMPLETED
    ).scalar()

    # Calculate overdue tasks: active tasks with due date in the past
    overdue_tasks = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.ACTIVE,
        Task.due_date < date.today()
    ).scalar()

    # Calculate priority breakdown for active tasks
    low_priority = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.ACTIVE,
        Task.priority == "LOW"  # This matches the enum value
    ).scalar()

    medium_priority = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.ACTIVE,
        Task.priority == "MEDIUM"  # This matches the enum value
    ).scalar()

    high_priority = session.query(func.count(Task.id)).filter(
        Task.user_id == user_id,
        Task.status == Status.ACTIVE,
        Task.priority == "HIGH"  # This matches the enum value
    ).scalar()

    return {
        "user_id": user_id,
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "priority_breakdown": {
            "low": low_priority,
            "medium": medium_priority,
            "high": high_priority
        },
        "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete user account."""
    # Users can only delete their own account, or admins can delete any account
    if current_user.id != user_id and not hasattr(current_user, 'is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    user = session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Soft delete by marking as inactive
    # In a real application, you might want to add a 'deleted_at' field
    user.is_active = False
    user.updated_at = user.updated_at

    session.commit()

    return {"message": "User account deactivated"}