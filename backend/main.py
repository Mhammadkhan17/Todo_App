#!/usr/bin/env python3
"""
FastAPI Todo Application Entry Point

Main application file that sets up and runs the FastAPI todo application.
Includes all routers, middleware, and startup events.
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

# Load .env BEFORE importing modules that read configuration at import time
# (src.database.engine captures DATABASE_URL when it is imported below).
load_dotenv()

from src.database.engine import database_engine
from src.models import *  # Import all models to register them with SQLModel
from src.api.tasks_router import router as tasks_router
from src.api.users_router import router as users_router
from src.auth.auth_router import router as auth_router
from src.api.v1.rag import router as rag_router
from src.api.chat_router import router as chat_router
from src.schemas import HealthCheckResponse
from src.middleware.exception_handlers import (
    todo_exception_handler, validation_exception_handler,
    integrity_error_handler, sqlalchemy_error_handler,
    http_exception_handler, general_exception_handler
)
from src.exceptions.custom_exceptions import (
    TodoException, UserNotFoundException, TaskNotFoundException,
    UserAlreadyExistsException, AuthenticationException,
    AuthorizationException, DatabaseException, ValidationErrorException,
    MissingRequiredFieldException, InvalidDateRangeException
)
from src.security.middleware import SecurityMiddleware, InputValidationMiddleware
from src.security.cors import CORSSecurity


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Todo Application")
    try:
        # Test database connection
        if database_engine.test_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Database connection failed")
            raise Exception("Database connection failed")

        # Create tables if they don't exist
        database_engine.create_all_tables()
        logger.info("Database tables verified/created")

        # Additive columns create_all cannot add to existing tables
        database_engine.ensure_rag_document_columns()
        logger.info("RAG document schema verified/updated")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Todo Application")
    database_engine.close()


# Create FastAPI application
app = FastAPI(
    title="Todo API",
    description="RESTful API for Todo Management Application",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Register exception handlers
app.add_exception_handler(TodoException, todo_exception_handler)
app.add_exception_handler(UserNotFoundException, todo_exception_handler)
app.add_exception_handler(TaskNotFoundException, todo_exception_handler)
app.add_exception_handler(UserAlreadyExistsException, todo_exception_handler)
app.add_exception_handler(AuthenticationException, todo_exception_handler)
app.add_exception_handler(AuthorizationException, todo_exception_handler)
app.add_exception_handler(DatabaseException, todo_exception_handler)
app.add_exception_handler(ValidationErrorException, todo_exception_handler)
app.add_exception_handler(MissingRequiredFieldException, todo_exception_handler)
app.add_exception_handler(InvalidDateRangeException, todo_exception_handler)

# Add other exception handlers
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Configure middleware
# Enhanced CORS middleware with security controls
CORSSecurity.add_cors_middleware(app)

# Security middleware with rate limiting and validation
# Allow all hosts in production to support Hugging Face subdomains
allowed_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "todo_app_backend_dev", "postgres", "*"]

app.add_middleware(
    SecurityMiddleware,
    allowed_hosts=allowed_hosts,
    rate_limit_enabled=True,
    rate_limit_attempts=100,
    rate_limit_window_minutes=15,
    security_headers_enabled=True
)

# Input validation middleware
app.add_middleware(InputValidationMiddleware)

# Trusted host middleware (security)
# Disable in production (Hugging Face) as the ingress proxy handles host validation.
if os.getenv("ENVIRONMENT") == "development":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
    )

# HTTPS redirect middleware (enable in production)
if os.getenv("USE_HTTPS", "false").lower() == "true":
    app.add_middleware(HTTPSRedirectMiddleware)


# Root endpoint
@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint for health check."""
    return HealthCheckResponse(
        status="ok",
        message="Todo API is running",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="ok",
        message="Service is healthy",
        version="1.0.0"
    )


# Include routers
app.include_router(
    auth_router,
    prefix="/api",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix="/api",
    tags=["Users"]
)

app.include_router(
    tasks_router,
    prefix="/api",
    tags=["Tasks"]
)

app.include_router(
    rag_router,
    prefix="/api",
    tags=["RAG Chatbot"]
)

app.include_router(
    chat_router,
    prefix="/api",
    tags=["Chat"]
)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )