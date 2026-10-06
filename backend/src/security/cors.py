#!/usr/bin/env python3
"""
CORS Configuration

Enhanced CORS configuration with security controls.
"""

import os
from typing import List, Optional, Callable
from fastapi.middleware.cors import CORSMiddleware

from src.security.config import SecuritySettings


class CORSSecurity:
    """Enhanced CORS security configuration."""

    @staticmethod
    def get_allowed_origins() -> List[str]:
        """Get allowed origins from environment or defaults."""

        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")

        if allowed_origins_str:
            # Parse comma-separated origins
            origins = [origin.strip() for origin in allowed_origins_str.split(",")]
            return origins
        else:
            # Default to localhost in development
            if SecuritySettings.ENVIRONMENT == "development":
                return [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:8000",
                    "http://127.0.0.1:8000"
                ]
            else:
                # In production, require explicit configuration
                raise ValueError(
                    "ALLOWED_ORIGINS must be explicitly configured in production environment"
                )

    @staticmethod
    def is_origin_allowed(origin: str) -> bool:
        """Check if origin is allowed."""

        if not origin:
            return False

        allowed_origins = CORSSecurity.get_allowed_origins()

        # Exact match
        if origin in allowed_origins:
            return True

        # Subdomain matching (if configured)
        for allowed_origin in allowed_origins:
            if allowed_origin.startswith("https://") and origin.startswith("https://"):
                # Allow subdomains
                allowed_domain = allowed_origin.replace("https://", "")
                origin_domain = origin.replace("https://", "")

                if origin_domain.endswith("." + allowed_domain):
                    return True

        return False

    @staticmethod
    def create_cors_middleware_config() -> dict:
        """Create CORS middleware configuration with security settings."""

        allowed_origins = CORSSecurity.get_allowed_origins()

        config = {
            "allow_origins": allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "Origin",
                "X-CSRFToken"
            ],
            "expose_headers": [
                "X-Total-Count",
                "X-Page-Size",
                "X-Current-Page"
            ],
            "max_age": 600  # 10 minutes
        }

        # Add origin validation function in production
        if SecuritySettings.ENVIRONMENT == "production":
            config["allow_origin_regex"] = None  # Disable regex in production for security

        return config

    @staticmethod
    def add_cors_middleware(app):
        """Add CORS middleware to FastAPI application."""

        cors_config = CORSSecurity.create_cors_middleware_config()

        app.add_middleware(
            CORSMiddleware,
            **cors_config
        )

        return app


class SecureCORSMiddleware:
    """Custom CORS middleware with additional security controls."""

    def __init__(
        self,
        app,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
        allow_origin_regex: Optional[str] = None
    ):
        self.app = app
        self.allow_origins = allow_origins or []
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        self.allow_origin_regex = allow_origin_regex

    async def __call__(self, scope, receive, send):
        """Process CORS requests with security controls."""

        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        origin = self._get_origin(scope)
        method = scope.get("method", "").upper()

        # Check if origin is allowed
        if origin and not self._is_origin_allowed(origin):
            await self._send_cors_preflight_response(scope, send, status_code=403)
            return

        # Handle preflight requests
        if method == "OPTIONS":
            await self._handle_preflight_request(scope, send, origin)
            return

        # Add CORS headers to response
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                if origin:
                    headers[b"access-control-allow-origin"] = origin.encode()

                if self.allow_credentials:
                    headers[b"access-control-allow-credentials"] = b"true"

                if self.max_age:
                    headers[b"access-control-max-age"] = str(self.max_age).encode()

                # Remove content-length for CORS
                headers.pop(b"content-length", None)

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_with_cors)

    def _get_origin(self, scope) -> Optional[str]:
        """Get origin from request scope."""

        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin")

        if origin:
            return origin.decode()

        return None

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed with security controls."""

        # Deny null origin
        if origin == "null":
            return False

        # Check exact matches
        if origin in self.allow_origins:
            return True

        # Check regex pattern if provided
        if self.allow_origin_regex:
            import re
            if re.match(self.allow_origin_regex, origin):
                return True

        return False

    async def _handle_preflight_request(self, scope, send, origin: Optional[str]):
        """Handle CORS preflight requests."""

        headers = []

        if origin:
            headers.append((b"access-control-allow-origin", origin.encode()))

        if self.allow_credentials:
            headers.append((b"access-control-allow-credentials", b"true"))

        headers.extend([
            (b"access-control-allow-methods", ", ".join(self.allow_methods).encode()),
            (b"access-control-allow-headers", ", ".join(self.allow_headers).encode()),
            (b"access-control-max-age", str(self.max_age).encode()),
            (b"vary", b"Origin")
        ])

        await send({
            "type": "http.response.start",
            "status": 204,
            "headers": headers
        })

        await send({
            "type": "http.response.body",
            "body": b""
        })

    async def _send_cors_preflight_response(self, scope, send, status_code: int = 403):
        """Send CORS error response."""

        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"access-control-allow-origin", b"*")
            ]
        })

        await send({
            "type": "http.response.body",
            "body": b"Origin not allowed"
        })


def get_cors_config() -> dict:
    """Get CORS configuration from security settings."""

    return {
        "allow_origins": CORSSecurity.get_allowed_origins(),
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "Accept",
            "Origin",
            "X-CSRFToken"
        ],
        "expose_headers": [
            "X-Total-Count",
            "X-Page-Size",
            "X-Current-Page"
        ],
        "max_age": 600
    }