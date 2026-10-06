#!/usr/bin/env python3
"""
Custom Exceptions

Custom exception classes for the todo application.
"""

from fastapi import HTTPException, status
from typing import Optional, List


class TodoException(HTTPException):
    """Base exception for todo application."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UserNotFoundException(TodoException):
    """Exception raised when user is not found."""

    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )


class TaskNotFoundException(TodoException):
    """Exception raised when task is not found."""

    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )


class UserAlreadyExistsException(TodoException):
    """Exception raised when user already exists."""

    def __init__(self, email_or_username: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email or username '{email_or_username}' already exists"
        )


class AuthenticationException(TodoException):
    """Exception raised for authentication errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(TodoException):
    """Exception raised for authorization errors."""

    def __init__(self, detail: str = "Not authorized"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class DatabaseException(TodoException):
    """Exception raised for database errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {detail}"
        )


class ValidationErrorException(TodoException):
    """Exception raised for validation errors."""

    def __init__(self, field: str, value: str, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error in field '{field}': {message}. Value: {value}"
        )


class MissingRequiredFieldException(TodoException):
    """Exception raised when required fields are missing."""

    def __init__(self, field: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Required field '{field}' is missing"
        )


class InvalidDateRangeException(TodoException):
    """Exception raised when date range is invalid."""

    def __init__(self, message: str = "Invalid date range"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message
        )