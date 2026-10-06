#!/usr/bin/env python3
"""
Exception Handlers

Custom exception handlers for FastAPI application.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from datetime import datetime

from src.exceptions.custom_exceptions import (
    TodoException, UserNotFoundException, TaskNotFoundException,
    UserAlreadyExistsException, AuthenticationException,
    AuthorizationException, DatabaseException, ValidationErrorException,
    MissingRequiredFieldException, InvalidDateRangeException
)

logger = logging.getLogger(__name__)


async def todo_exception_handler(request: Request, exc: TodoException):
    """Handle custom todo exceptions."""
    logger.error(f"TodoException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Todo Application Error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": [
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "value": error.get("input", None)
                }
                for error in exc.errors()
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    logger.error(f"Integrity error: {exc}")
    return JSONResponse(
        status_code=409,
        content={
            "error": "Database Integrity Error",
            "message": "A database constraint was violated",
            "details": str(exc.orig),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy errors."""
    logger.error(f"SQLAlchemy error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database Error",
            "message": "A database error occurred",
            "details": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"General exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "details": str(exc) if hasattr(exc, '__str__') else "Unknown error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )