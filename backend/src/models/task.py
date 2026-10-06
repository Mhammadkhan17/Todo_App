#!/usr/bin/env python3
"""
Task Model

Defines the Task model for the todo application with user relationships.
Uses SQLModel for ORM with PostgreSQL database.
"""

from datetime import date, datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator, BaseModel
from enum import Enum


class Priority(str, Enum):
    """Task priority levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Status(str, Enum):
    """Task status levels."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class Task(SQLModel, table=True):
    """Task model representing a todo item."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description"
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Task priority level"
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Task due date"
    )
    status: Status = Field(
        default=Status.ACTIVE,
        description="Task status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Task creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Task completion timestamp"
    )

    # Foreign key relationship
    user_id: int = Field(
        foreign_key="users.id",
        description="User who owns this task"
    )

    # Relationship to User
    user: Optional["User"] = Relationship(back_populates="tasks")

    # Table configuration
    __tablename__ = "tasks"

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate task title."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate due date is not in the past."""
        if v and v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v

    def toggle_completion(self) -> None:
        """Toggle task completion status."""
        if self.status == Status.ACTIVE:
            self.status = Status.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
        else:
            self.status = Status.ACTIVE
            self.completed_at = None

    def update_status(self, status: Status) -> None:
        """Update task status."""
        self.status = status
        if status == Status.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)
        else:
            self.completed_at = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
        from_attributes = True


# Additional Task Model Classes
class TaskBase(BaseModel):
    """Base model for task fields."""
    title: str
    description: Optional[str] = None
    priority: Optional[Priority] = Priority.MEDIUM
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    """Model for creating a new task."""
    title: str

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate task title."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate due date is not in the past."""
        if v and v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v


class TaskUpdate(BaseModel):
    """Model for updating task fields."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    status: Optional[Status] = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate task title."""
        if v and len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        return v.strip() if v else v

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Validate due date is not in the past."""
        if v and v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v


class TaskPublic(TaskBase):
    """Model for returning public task information."""
    id: int
    status: Status
    user_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# Import User here to avoid circular import issues
from .user import User

# Update the User model to include the relationship
User.tasks = Relationship(back_populates="user")