#!/usr/bin/env python3
"""
Authentication Router

FastAPI router for authentication endpoints.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Body
from sqlalchemy.orm import Session

from src.schemas.user import UserCreate, UserResponse, Token, UserLogin, TokenData
from src.models.user import User
from src.auth.auth_service import AuthService
from src.auth.jwt_service import JWTService
from src.database.session import get_session
from src.dependencies import get_current_user


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, session: Session = Depends(get_session)):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )

        # Create new user
        hashed_password = AuthService.get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            full_name=user_data.full_name
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Login and get access token."""
    user = AuthService.authenticate_user(
        form_data.username,
        form_data.password,
        session=session,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use enhanced JWT service for token creation
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "email": user.email
    }

    token_response = JWTService.create_access_token(
        token_data,
        include_refresh=True
    )

    return {
        "access_token": token_response["access_token"],
        "refresh_token": token_response["refresh_token"],
        "token_type": token_response["token_type"],
        "expires_in": token_response["expires_in"],
        "user_id": user.id,
        "expires_at": token_response["expires_at"]
    }


@router.post("/token", response_model=Token)
async def get_token_for_user(
    user_data: UserLogin,
    session: Session = Depends(get_session),
):
    """Get access token using username/password (alternative to form login)."""
    user = AuthService.authenticate_user(
        user_data.username,
        user_data.password,
        session=session,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use enhanced JWT service for token creation
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "email": user.email
    }

    token_response = JWTService.create_access_token(
        token_data,
        include_refresh=True
    )

    return {
        "access_token": token_response["access_token"],
        "refresh_token": token_response["refresh_token"],
        "token_type": token_response["token_type"],
        "expires_in": token_response["expires_in"],
        "user_id": user.id,
        "expires_at": token_response["expires_at"]
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    """Refresh access token using refresh token."""
    try:
        # Use enhanced JWT service for token refresh
        token_response = JWTService.refresh_access_token(refresh_token)

        # Decode the refresh token to get user_id
        from src.auth.jwt_service import SecurityConfig, jwt
        from src.exceptions.custom_exceptions import AuthenticationException

        try:
            payload = jwt.decode(
                refresh_token,
                SecurityConfig.SECRET_KEY,
                algorithms=[SecurityConfig.ALGORITHM]
            )
            user_id = payload.get("user_id")
        except Exception:
            raise AuthenticationException("Invalid refresh token")

        return {
            "access_token": token_response["access_token"],
            "refresh_token": token_response.get("refresh_token"),
            "token_type": token_response["token_type"],
            "expires_in": token_response["expires_in"],
            "user_id": user_id,
            "expires_at": token_response.get("expires_at")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/revoke")
async def revoke_token(
    token: str = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """Revoke an access token (logout)."""
    try:
        # Verify that the token belongs to the current user
        token_data = JWTService.verify_access_token(token)

        if token_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke token that does not belong to you"
            )

        # In a production system, this would add the token to a blacklist/revocation list
        # For now, we'll just verify that the token is valid and belongs to the user
        revoked = JWTService.revoke_token(token)

        return {
            "success": True,
            "message": "Token revoked successfully" if revoked else "Token may have already expired"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )


@router.post("/verify-token")
async def verify_token(token: str = Body(..., embed=True)):
    """Verify if a token is valid."""
    try:
        token_data = JWTService.verify_access_token(token)
        return {
            "valid": True,
            "username": token_data.username,
            "user_id": token_data.user_id,
            "message": "Token is valid"
        }
    except Exception as e:
        # Don't expose internal error details
        return {"valid": False, "error": "Invalid token"}