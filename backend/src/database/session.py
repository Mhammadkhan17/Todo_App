#!/usr/bin/env python3
"""
Database Session Management

Provides session management utilities and dependency injection
for FastAPI applications using SQLModel.
"""

from typing import Generator
from contextlib import contextmanager
from sqlmodel import Session, select
from fastapi import Depends, HTTPException, status

from ..database.engine import database_engine
from ..models.user import User
from ..models.task import Task


class DatabaseSession:
    """Database session manager with convenience methods."""

    def __init__(self, session: Session):
        """
        Initialize session manager.

        Args:
            session: SQLModel session instance
        """
        self.session = session

    def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    def get_user_by_email(self, email: str) -> User:
        """Get user by email."""
        user = self.session.exec(
            select(User).where(User.email == email)
        ).first()
        return user

    def get_user_by_username(self, username: str) -> User:
        """Get user by username."""
        user = self.session.exec(
            select(User).where(User.username == username)
        ).first()
        return user

    def get_task_by_id(self, task_id: int, user_id: int) -> Task:
        """Get task by ID for specific user."""
        task = self.session.get(Task, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        if task.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        return task

    def get_tasks_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> list[Task]:
        """Get all tasks for a specific user."""
        tasks = self.session.exec(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return list(tasks)

    def get_tasks_by_status(self, user_id: int, status: str, limit: int = 100, offset: int = 0) -> list[Task]:
        """Get tasks by status for a specific user."""
        from ..models.task import Status
        try:
            task_status = Status(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

        tasks = self.session.exec(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.status == task_status)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return list(tasks)

    def get_tasks_by_priority(self, user_id: int, priority: str, limit: int = 100, offset: int = 0) -> list[Task]:
        """Get tasks by priority for a specific user."""
        from ..models.task import Priority
        try:
            task_priority = Priority(priority.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid priority value"
            )

        tasks = self.session.exec(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.priority == task_priority)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return list(tasks)

    def get_overdue_tasks(self, user_id: int) -> list[Task]:
        """Get overdue tasks for a specific user."""
        from datetime import date
        tasks = self.session.exec(
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.status == "ACTIVE")
            .where(Task.due_date < date.today())
            .order_by(Task.due_date.asc())
        ).all()
        return list(tasks)

    def create_user(self, user: User) -> User:
        """Create a new user."""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_user(self, user: User) -> User:
        """Update user information."""
        from datetime import datetime, timezone
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user: User) -> None:
        """Delete a user and their tasks."""
        # Delete all tasks first (due to foreign key constraints)
        self.session.exec(
            select(Task).where(Task.user_id == user.id)
        ).delete()
        self.session.delete(user)
        self.session.commit()

    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def update_task(self, task: Task) -> Task:
        """Update task information."""
        from datetime import datetime, timezone
        task.updated_at = datetime.now(timezone.utc)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete_task(self, task: Task) -> None:
        """Delete a task."""
        self.session.delete(task)
        self.session.commit()


# Dependency injection for FastAPI
def get_database_session() -> Generator[DatabaseSession, None, None]:
    """
    FastAPI dependency to get database session.

    Usage in FastAPI endpoints:
        @app.get("/users/{user_id}")
        def get_user(user_id: int, db: DatabaseSession = Depends(get_database_session)):
            return db.get_user_by_id(user_id)
    """
    with database_engine.get_session() as session:
        yield DatabaseSession(session)


# Legacy session dependency (if needed for compatibility)
def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get raw SQLModel session.

    Usage in FastAPI endpoints:
        @app.get("/users/{user_id}")
        def get_user(user_id: int, session: Session = Depends(get_session)):
            return session.get(User, user_id)
    """
    with database_engine.get_session() as session:
        yield session