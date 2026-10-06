#!/usr/bin/env python3
"""
Input Validation and Sanitization

Comprehensive input validation and sanitization framework for security.
"""

import re
import html
import logging
from typing import Any, Optional, Union, List
from pydantic import ValidationError, validator
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class InputValidator:
    """Security-focused input validation and sanitization."""

    # Security patterns
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"(?i)(script|javascript|vbscript|onload|onerror|onmouseover)",
        r"(?i)(drop\s+table|create\s+table|insert\s+into|delete\s+from)",
        r"(?i)(xp_cmdshell|sp_|sys\.)",
        r"(?i)(\s*;\s*|\s*--\s*|\s*\/\*|\s*\*\/\s*)"
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
        r"javascript:",
        r"vbscript:",
        r"data:text/html",
        r"on\w+\s*="
    ]

    # Input size limits
    MAX_STRING_LENGTH = 10000
    MAX_EMAIL_LENGTH = 254
    MAX_USERNAME_LENGTH = 50
    MAX_PASSWORD_LENGTH = 128

    @classmethod
    def sanitize_string(cls, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input by removing potentially dangerous content."""

        if not value:
            return ""

        # Limit length
        if max_length and len(value) > max_length:
            value = value[:max_length]

        # Remove null bytes
        value = value.replace('\x00', '')

        # HTML encode
        value = html.escape(value, quote=True)

        # Remove control characters (except tab, newline, carriage return)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', value)

        return value.strip()

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate and sanitize email address."""

        if not email:
            raise ValueError("Email is required")

        email = email.strip().lower()

        if len(email) > cls.MAX_EMAIL_LENGTH:
            raise ValueError(f"Email too long (max {cls.MAX_EMAIL_LENGTH} characters)")

        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")

        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', "'", ';', '&', '|', '$', '`']
        for char in dangerous_chars:
            if char in email:
                raise ValueError(f"Email contains invalid character: {char}")

        return cls.sanitize_string(email, cls.MAX_EMAIL_LENGTH)

    @classmethod
    def validate_username(cls, username: str) -> str:
        """Validate and sanitize username."""

        if not username:
            raise ValueError("Username is required")

        username = username.strip()

        if len(username) > cls.MAX_USERNAME_LENGTH:
            raise ValueError(f"Username too long (max {cls.MAX_USERNAME_LENGTH} characters)")

        # Username format: alphanumeric and underscore only
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValueError("Username can only contain letters, numbers, and underscores")

        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, username, re.IGNORECASE):
                raise ValueError("Username contains invalid characters")

        return cls.sanitize_string(username, cls.MAX_USERNAME_LENGTH)

    @classmethod
    def validate_password(cls, password: str) -> str:
        """Validate password strength and security."""

        if not password:
            raise ValueError("Password is required")

        if len(password) > cls.MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password too long (max {cls.MAX_PASSWORD_LENGTH} characters)")

        # Password strength requirements
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for common weak patterns
        weak_patterns = [
            r'password',
            r'123456',
            r'qwerty',
            r'admin',
            r'test'
        ]

        password_lower = password.lower()
        for pattern in weak_patterns:
            if pattern in password_lower:
                raise ValueError("Password is too common")

        # Require at least one uppercase, lowercase, digit, and special character
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r'\d', password):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")

        return password  # Don't sanitize passwords, just validate

    @classmethod
    def validate_task_title(cls, title: str) -> str:
        """Validate task title."""

        if not title:
            raise ValueError("Task title is required")

        if len(title) > 200:
            raise ValueError("Task title too long (max 200 characters)")

        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                raise ValueError("Task title contains invalid characters")

        return cls.sanitize_string(title, 200)

    @classmethod
    def validate_task_description(cls, description: Optional[str]) -> Optional[str]:
        """Validate task description."""

        if description is None:
            return None

        if len(description) > cls.MAX_STRING_LENGTH:
            raise ValueError(f"Description too long (max {cls.MAX_STRING_LENGTH} characters)")

        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, description, re.IGNORECASE):
                raise ValueError("Description contains invalid characters")

        return cls.sanitize_string(description, cls.MAX_STRING_LENGTH)

    @classmethod
    def validate_priority(cls, priority: str) -> str:
        """Validate task priority."""

        valid_priorities = ['low', 'medium', 'high']
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

        return priority

    @classmethod
    def validate_status(cls, status: str) -> str:
        """Validate task status."""

        valid_statuses = ['pending', 'in_progress', 'completed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        return status

    @classmethod
    def validate_integer_range(cls, value: int, min_val: int, max_val: int, field_name: str) -> int:
        """Validate integer is within specified range."""

        if not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer")

        if value < min_val or value > max_val:
            raise ValueError(f"{field_name} must be between {min_val} and {max_val}")

        return value

    @classmethod
    def validate_boolean(cls, value: Any) -> bool:
        """Validate boolean value."""

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            value = value.lower()
            if value in ['true', '1', 'yes', 'on']:
                return True
            elif value in ['false', '0', 'no', 'off']:
                return False

        raise ValueError("Value must be a boolean")

    @classmethod
    def sanitize_sql_input(cls, value: str) -> str:
        """Sanitize input for SQL queries."""

        if not value:
            return ""

        # Remove SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)

        # Escape single quotes
        value = value.replace("'", "''")

        return value

    @classmethod
    def validate_pagination_params(
        cls,
        page: int,
        size: int,
        max_page: int = 1000,
        max_size: int = 100
    ) -> tuple:
        """Validate pagination parameters."""

        page = cls.validate_integer_range(page, 1, max_page, "page")
        size = cls.validate_integer_range(size, 1, max_size, "size")

        return page, size

    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate and sanitize search query."""

        if not query:
            raise ValueError("Search query is required")

        # Basic length check
        if len(query) > 500:
            raise ValueError("Search query too long (max 500 characters)")

        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError("Search query contains invalid characters")

        return cls.sanitize_string(query, 500)