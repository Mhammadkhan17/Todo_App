#!/usr/bin/env python3
"""
User Schemas

Pydantic models for user-related API requests and responses.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from src.models.task import Priority


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (alphanumeric and underscore only)"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's full name"
    )


class UserCreate(UserBase):
    """User creation request model."""
    password: str = Field(
        ...,
        min_length=8,
        description="User password (minimum 8 characters)"
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """User update request model."""
    email: Optional[EmailStr] = Field(default=None)
    full_name: Optional[str] = Field(default=None, max_length=100)


class UserResponse(UserBase):
    """User response model."""
    id: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """User login request model."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: int
    user_id: int
    expires_at: Optional[str] = None


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    user_id: Optional[int] = None