#!/usr/bin/env python3
"""
Security Middleware

Comprehensive security middleware for rate limiting, input validation, and security headers.
"""

import os
import time
import hashlib
import logging
from typing import Dict, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware providing rate limiting and security headers."""

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: Optional[List[str]] = None,
        rate_limit_enabled: bool = True,
        rate_limit_attempts: int = 100,
        rate_limit_window_minutes: int = 15,
        security_headers_enabled: bool = True
    ):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1"]
        self.rate_limit_enabled = rate_limit_enabled
        self.rate_limit_attempts = rate_limit_attempts
        self.rate_limit_window_minutes = rate_limit_window_minutes
        self.security_headers_enabled = security_headers_enabled

        # Rate limiting storage
        self.rate_limit_storage: Dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""

        # 1. Host validation
        if not self._validate_host(request):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid host"
            )

        # 2. Rate limiting
        if self.rate_limit_enabled:
            if not self._check_rate_limit(request):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(self.rate_limit_window_minutes * 60)}
                )

        # 3. Process request
        response = await call_next(request)

        # 4. Add security headers
        if self.security_headers_enabled:
            self._add_security_headers(response, request.url.path)

        return response

    def _validate_host(self, request: Request) -> bool:
        """Validate request host against allowed hosts."""
        host = request.headers.get("host", "")
        if host not in self.allowed_hosts and "*" not in self.allowed_hosts:
            logger.warning(f"Blocked request from unauthorized host: {host}")
            return False
        return True

    def _check_rate_limit(self, request: Request) -> bool:
        """Check if request exceeds rate limit."""

        # Get client identifier (IP + User-Agent hash)
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        client_id = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.rate_limit_window_minutes)

        # Clean old entries
        request_times = self.rate_limit_storage[client_id]
        while request_times and request_times[0] < window_start:
            request_times.popleft()

        # Check limit
        if len(request_times) >= self.rate_limit_attempts:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False

        # Add current request
        request_times.append(now)
        return True

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request headers."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

    # Swagger UI / ReDoc pull their bundles from CDNs and FastAPI renders the
    # Swagger bootstrap as an inline <script>, so the default `default-src 'self'`
    # policy renders /api/docs blank. Relax the policy only for the docs paths.
    _DOCS_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.redoc.ly; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.redoc.ly; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "frame-ancestors 'self' https://*.hf.space https://huggingface.co;"
    )
    _DOCS_PATH_PREFIXES = (
        "/api/docs",
        "/api/redoc",
        "/api/openapi",
        "/api/oauth2-redirect",
    )

    def _add_security_headers(self, response: Response, path: str = "") -> None:
        """Add security headers to response."""

        # Basic security headers
        # X-Frame-Options is set to SAMEORIGIN to allow Hugging Face to iframe the app
        # Hugging Face Spaces require the app to be embeddable.
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen"
        }

        # HTTPS redirect headers (if enabled)
        if os.getenv("USE_HTTPS", "false").lower() == "true":
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        # Allow Hugging Face domains to frame the application
        default_csp = "default-src 'self'; frame-ancestors 'self' https://*.hf.space https://huggingface.co;"
        if os.getenv("CSP_POLICY"):
            csp = os.getenv("CSP_POLICY")
        elif path.startswith(self._DOCS_PATH_PREFIXES):
            csp = self._DOCS_CSP
        else:
            csp = default_csp
        security_headers["Content-Security-Policy"] = csp

        # Add headers to response
        for key, value in security_headers.items():
            if key not in response.headers:
                response.headers[key] = value


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation and sanitization."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through input validation middleware."""

        # Log request for security monitoring
        await self._log_request(request)

        # Validate request size
        if not await self._validate_request_size(request):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )

        # Validate content type
        if not self._validate_content_type(request):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported media type"
            )

        # Process request
        response = await call_next(request)

        return response

    async def _log_request(self, request: Request) -> None:
        """Log request for security monitoring."""
        logger.info(
            f"Request: {request.method} {request.url} "
            f"from {request.client.host if request.client else 'unknown'} "
            f"User-Agent: {request.headers.get('user-agent', 'none')}"
        )

    async def _validate_request_size(self, request: Request) -> bool:
        """Validate request body size."""

        # Get content length
        content_length = request.headers.get("content-length")
        if not content_length:
            return True  # No content length header, assume OK

        try:
            size = int(content_length)
            max_size = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB default

            if size > max_size:
                logger.warning(f"Request too large: {size} bytes")
                return False

            return True
        except ValueError:
            logger.warning("Invalid content-length header")
            return False

    def _validate_content_type(self, request: Request) -> bool:
        """Validate request content type."""

        # Skip validation for GET, OPTIONS, and PATCH requests without body
        # OPTIONS requests are part of CORS preflight and typically don't have Content-Type
        # PATCH requests for toggle operations might not have a body
        if request.method in ["GET", "OPTIONS", "HEAD"]:
            return True

        # Also skip validation if there's no content-type header (no body)
        content_type = request.headers.get("content-type", "")
        if not content_type:
            return True

        content_type = request.headers.get("content-type", "")
        allowed_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data"
        ]

        # Check if content type is allowed
        for allowed_type in allowed_types:
            if content_type.startswith(allowed_type):
                return True

        logger.warning(f"Invalid content type: {content_type}")
        return False


class CORSHandler:
    """Enhanced CORS handler with security controls."""

    @staticmethod
    def get_cors_middleware_config():
        """Get CORS middleware configuration with security settings."""

        # Get allowed origins from environment
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
        allowed_origins = []

        if allowed_origins_str:
            allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
        else:
            # Default to localhost in development
            if os.getenv("ENVIRONMENT", "development") == "development":
                allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
            else:
                logger.warning("ALLOWED_ORIGINS not configured for production")

        return {
            "allow_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "Origin"
            ],
            "expose_headers": ["X-Total-Count"],
            "max_age": 600  # 10 minutes
        }