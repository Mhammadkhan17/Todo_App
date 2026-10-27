#!/usr/bin/env python3
"""
Authentication Service

Handles JWT token generation, verification, and user authentication.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.auth.jwt_service import JWTService
from src.database.engine import database_engine
from src.database.session import get_session
from src.models.user import User
from src.schemas.user import TokenData

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "todo_app_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


class AuthService:
    """Authentication service for handling user authentication and JWT tokens."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return JWTService.verify_password(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return JWTService.get_password_hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> dict:
        """Create a JWT access token with enhanced security."""
        return JWTService.create_access_token(data, expires_delta)

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Verify a JWT token and return token data."""
        return JWTService.verify_access_token(token)

    @staticmethod
    def _authenticate(session: Session, username: str, password: str) -> User | None:
        user = session.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        user.last_login_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(user)

        return User(
            id=user.id,
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            email_verified=user.email_verified,
            verification_token=user.verification_token,
            password_reset_token=user.password_reset_token,
            password_reset_expires=user.password_reset_expires,
        )

    @staticmethod
    def authenticate_user(
        username: str,
        password: str,
        session: Session | None = None,
    ) -> User | None:
        try:
            if session is not None:
                return AuthService._authenticate(session, username, password)
            with database_engine.get_session() as own_session:
                return AuthService._authenticate(own_session, username, password)
        except Exception as e:  # noqa: BLE001 - map any failure to HTTP 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {e!s}",
            )

    @staticmethod
    def get_user_by_id(user_id: int) -> User | None:
        """Get user by ID."""
        try:
            with get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                return user
        except Exception:  # noqa: BLE001 - lookup helper: treat any failure as "not found"
            return None

    @staticmethod
    def get_user_by_username(username: str) -> User | None:
        """Get user by username."""
        try:
            with get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                return user
        except Exception:  # noqa: BLE001 - lookup helper: treat any failure as "not found"
            return None

    @staticmethod
    def get_user_by_email(email: str) -> User | None:
        """Get user by email."""
        try:
            with get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                return user
        except Exception:  # noqa: BLE001 - lookup helper: treat any failure as "not found"
            return None

    @staticmethod
    def create_user(email: str, username: str, password: str, full_name: str | None = None) -> User:
        """Create a new user."""
        try:
            with get_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter(
                    (User.email == email) | (User.username == username)
                ).first()

                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this email or username already exists"
                    )

                # Create new user
                hashed_password = AuthService.get_password_hash(password)
                user = User(
                    email=email,
                    username=username,
                    password_hash=hashed_password,
                    full_name=full_name
                )

                session.add(user)
                session.commit()
                session.refresh(user)

                return user

        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001 - map any failure to HTTP 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {e!s}"
            )