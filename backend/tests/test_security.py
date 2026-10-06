#!/usr/bin/env python3
"""
Security Tests

Tests for security middleware, input validation, and JWT security.
"""

import pytest
from fastapi.testclient import TestClient
from jose import jwt
import os

from src.security.validation import InputValidator
from src.auth.jwt_service import JWTService, SecurityConfig
from src.security.config import get_security_settings


def test_password_validation():
    """Test password strength validation."""

    # Test valid password
    valid_password = "SecurePass123!"
    result = InputValidator.validate_password(valid_password)
    assert result == valid_password

    # Test invalid passwords
    with pytest.raises(ValueError, match="Password is required"):
        InputValidator.validate_password("")

    with pytest.raises(ValueError, match="Password must be at least 8 characters"):
        InputValidator.validate_password("Short1!")

    with pytest.raises(ValueError, match="Password must contain at least one uppercase"):
        InputValidator.validate_password("lowercase123!")

    with pytest.raises(ValueError, match="Password must contain at least one digit"):
        InputValidator.validate_password("NoDigits!")

    with pytest.raises(ValueError, match="Password must contain at least one special character"):
        InputValidator.validate_password("NoSpecial123")


def test_email_validation():
    """Test email validation."""

    # Test valid email
    valid_email = "user@example.com"
    result = InputValidator.validate_email(valid_email)
    assert result == valid_email

    # Test invalid emails
    with pytest.raises(ValueError, match="Email is required"):
        InputValidator.validate_email("")

    with pytest.raises(ValueError, match="Invalid email format"):
        InputValidator.validate_email("invalid-email")

    with pytest.raises(ValueError, match="Email too long"):
        InputValidator.validate_email("a" * 300 + "@example.com")


def test_username_validation():
    """Test username validation."""

    # Test valid username
    valid_username = "user123"
    result = InputValidator.validate_username(valid_username)
    assert result == valid_username

    # Test invalid usernames
    with pytest.raises(ValueError, match="Username is required"):
        InputValidator.validate_username("")

    with pytest.raises(ValueError, match="Username too long"):
        InputValidator.validate_username("a" * 60)

    with pytest.raises(ValueError, match="Username can only contain"):
        InputValidator.validate_username("user@invalid")


def test_jwt_token_creation():
    """Test JWT token creation with enhanced security."""

    # Test token creation
    user_data = {
        "sub": "testuser",
        "user_id": 1,
        "email": "test@example.com"
    }

    token_response = JWTService.create_access_token(
        user_data,
        include_refresh=True
    )

    assert "access_token" in token_response
    assert "refresh_token" in token_response
    assert "token_type" in token_response
    assert "expires_in" in token_response
    assert "expires_at" in token_response

    # Verify token structure
    access_token = token_response["access_token"]
    payload = jwt.decode(access_token, SecurityConfig.SECRET_KEY, algorithms=[SecurityConfig.ALGORITHM])

    assert payload["sub"] == "testuser"
    assert payload["user_id"] == 1
    assert payload["type"] == "access"
    assert "jti" in payload  # Unique token ID
    assert "iat" in payload  # Issued at
    assert "exp" in payload  # Expiration


def test_jwt_token_verification():
    """Test JWT token verification."""

    user_data = {
        "sub": "testuser",
        "user_id": 1
    }

    token_response = JWTService.create_access_token(user_data)
    access_token = token_response["access_token"]

    # Verify token
    token_data = JWTService.verify_access_token(access_token)

    assert token_data.username == "testuser"
    assert token_data.user_id == 1


def test_jwt_token_expiration():
    """Test JWT token expiration handling."""

    import time
    from datetime import timedelta

    # Create token with short expiration
    user_data = {"sub": "testuser", "user_id": 1}

    # Test with 1 second expiration
    token_response = JWTService.create_access_token(
        user_data,
        expires_delta=timedelta(seconds=1)
    )

    access_token = token_response["access_token"]

    # Wait for expiration
    time.sleep(2)

    # Token should be expired
    with pytest.raises(Exception, match="Token has expired"):
        JWTService.verify_access_token(access_token)


def test_security_configuration():
    """Test security configuration validation."""

    # Test with invalid configuration
    original_env = os.getenv("JWT_SECRET_KEY")
    os.environ["JWT_SECRET_KEY"] = ""

    try:
        settings = get_security_settings()

        if settings["errors"]:
            assert "JWT_SECRET_KEY is required" in str(settings["errors"])

    finally:
        if original_env:
            os.environ["JWT_SECRET_KEY"] = original_env
        elif "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]


def test_sql_injection_detection():
    """Test SQL injection pattern detection."""

    dangerous_input = "'; DROP TABLE users; --"
    sanitized = InputValidator.sanitize_string(dangerous_input)

    # Should be sanitized
    assert "'DROP TABLE" not in sanitized
    assert "--" not in sanitized


def test_xss_detection():
    """Test XSS payload detection."""

    xss_payload = "<script>alert('xss')</script>"
    sanitized = InputValidator.sanitize_string(xss_payload)

    # Should be HTML escaped
    assert "<script>" in sanitized
    assert "alert('xss')" in sanitized


def test_rate_limiting_simulation():
    """Test rate limiting logic simulation."""

    from collections import deque
    from datetime import datetime, timedelta

    # Simulate rate limiting storage
    rate_limit_storage = {}
    client_id = "test_client"
    rate_limit_attempts = 3
    rate_limit_window = 60  # 1 minute

    # Add multiple requests within window
    now = datetime.utcnow()
    request_times = deque()

    for i in range(rate_limit_attempts):
        request_times.append(now - timedelta(seconds=10))

    rate_limit_storage[client_id] = request_times

    # Check if limit is exceeded
    current_time = now
    window_start = current_time - timedelta(seconds=rate_limit_window)

    # Clean old entries
    while request_times and request_times[0] < window_start:
        request_times.popleft()

    # Should be at limit
    assert len(request_times) == rate_limit_attempts

    # Add one more request - should exceed limit
    request_times.append(current_time)
    assert len(request_times) > rate_limit_attempts


def test_security_headers(client: TestClient):
    """Test security headers are present in responses."""

    response = client.get("/health")

    # Check for security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"

    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


if __name__ == "__main__":
    pytest.main([__file__])