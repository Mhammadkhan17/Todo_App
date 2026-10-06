#!/usr/bin/env python3
"""
User Model

Defines the User model for the todo application with authentication support.
Uses SQLModel for ORM with PostgreSQL database.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from pydantic import EmailStr, field_validator, BaseModel
import secrets


class User(SQLModel, table=True):
    """User model representing a registered user in the system."""

    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(index=True, unique=True, description="User email address")
    username: str = Field(
        min_length=3,
        max_length=50,
        regex="^[a-zA-Z0-9_]+$",
        description="Unique username (alphanumeric and underscore only)"
    )
    password_hash: str = Field(description="Hashed password for authentication")
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User's full name"
    )
    is_active: bool = Field(default=True, description="Whether user account is active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Account creation timestamp")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp"
    )
    email_verified: bool = Field(default=False, description="Whether email has been verified")
    verification_token: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email verification token"
    )
    password_reset_token: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Password reset token"
    )
    password_reset_expires: Optional[datetime] = Field(
        default=None,
        description="Password reset token expiration time"
    )

    # Table configuration
    __tablename__ = "users"

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Username cannot be empty")
        if not v.isalnum() and '_' not in v:
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v.lower()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    def generate_verification_token(self) -> str:
        """Generate email verification token."""
        token = secrets.token_urlsafe(32)
        self.verification_token = token
        return token

    def generate_password_reset_token(self) -> str:
        """Generate password reset token."""
        from datetime import timedelta
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return token

    def verify_email(self) -> None:
        """Mark email as verified."""
        self.email_verified = True
        self.verification_token = None

    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Convert user to dictionary for serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "email_verified": self.email_verified
        }

    # Relationship to Tasks
    tasks: list["Task"] = Relationship(back_populates="user")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        from_attributes = True


# Additional User Model Classes
class UserBase(BaseModel):
    """Base model for user fields."""
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Username cannot be empty")
        if not v.replace('_', '').isalnum():
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v.lower()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class UserUpdate(BaseModel):
    """Model for updating user fields."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if v and (not v.replace('_', '').isalnum()):
            raise ValueError("Username must contain only alphanumeric characters and underscores")
        return v.lower() if v else v


class UserPublic(UserBase):
    """Model for returning public user information."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    email_verified: bool

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }