#!/usr/bin/env python3
"""
Task Schemas

Pydantic models for task-related API requests and responses.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
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


class TaskBase(BaseModel):
    """Base task model."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description"
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    due_date: Optional[date] = Field(default=None, description="Task due date")


class TaskCreate(TaskBase):
    """Task creation request model."""
    pass


class TaskUpdate(BaseModel):
    """Task update request model."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    status: Optional[Status] = None


class TaskResponse(TaskBase):
    """Task response model."""
    id: int
    status: Status
    user_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskFilter(BaseModel):
    """Task filtering parameters."""
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    search: Optional[str] = None

    @field_validator('due_date_to')
    @classmethod
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v and 'due_date_from' in values and values['due_date_from']:
            if v < values['due_date_from']:
                raise ValueError("due_date_to must be greater than or equal to due_date_from")
        return v


class TaskListResponse(BaseModel):
    """Task list response with pagination."""
    tasks: List[TaskResponse]
    total: int
    page: int
    size: int
    total_pages: int


class TaskCompletionToggle(BaseModel):
    """Task completion toggle response."""
    id: int
    status: Status
    completed_at: Optional[datetime] = None
    message: str