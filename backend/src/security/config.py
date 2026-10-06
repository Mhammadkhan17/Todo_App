#!/usr/bin/env python3
"""
Security Configuration

Centralized security configuration and settings management.
"""

import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SecuritySettings:
    """Security configuration settings."""

    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Password Security
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_MAX_LENGTH: int = int(os.getenv("PASSWORD_MAX_LENGTH", "128"))
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_ATTEMPTS: int = int(os.getenv("RATE_LIMIT_ATTEMPTS", "100"))
    RATE_LIMIT_WINDOW_MINUTES: int = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15"))

    # CORS Configuration
    CORS_ENABLED: bool = os.getenv("CORS_ENABLED", "true").lower() == "true"
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["Authorization", "Content-Type", "X-Requested-With"]

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true"
    CSP_POLICY: str = os.getenv("CSP_POLICY", "default-src 'self'")
    HSTS_MAX_AGE: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))

    # Input Validation
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
    MAX_STRING_LENGTH: int = int(os.getenv("MAX_STRING_LENGTH", "10000"))
    MAX_EMAIL_LENGTH: int = int(os.getenv("MAX_EMAIL_LENGTH", "254"))

    # Database Security
    DATABASE_SSL_MODE: str = os.getenv("DATABASE_SSL_MODE", "prefer")
    DATABASE_TIMEOUT: int = int(os.getenv("DATABASE_TIMEOUT", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG_MODE: bool = os.getenv("DEBUG", "false").lower() == "true"
    USE_HTTPS: bool = os.getenv("USE_HTTPS", "false").lower() == "true"

    @classmethod
    def validate_settings(cls) -> Dict[str, Any]:
        """Validate and return security settings."""

        errors = []

        # Validate JWT settings
        if not cls.JWT_SECRET_KEY:
            if cls.ENVIRONMENT == "production":
                errors.append("JWT_SECRET_KEY is required in production")
            else:
                logger.warning("JWT_SECRET_KEY not set, using fallback")

        if cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES < 5:
            errors.append("JWT_ACCESS_TOKEN_EXPIRE_MINUTES should be at least 5 minutes")

        if cls.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 90:
            errors.append("JWT_REFRESH_TOKEN_EXPIRE_DAYS should not exceed 90 days")

        # Validate password settings
        if cls.PASSWORD_MIN_LENGTH < 8:
            errors.append("PASSWORD_MIN_LENGTH should be at least 8 characters")

        if cls.PASSWORD_MAX_LENGTH > 128:
            errors.append("PASSWORD_MAX_LENGTH should not exceed 128 characters")

        # Validate rate limiting
        if cls.RATE_LIMIT_ATTEMPTS < 10:
            errors.append("RATE_LIMIT_ATTEMPTS should be at least 10")

        if cls.RATE_LIMIT_WINDOW_MINUTES < 1:
            errors.append("RATE_LIMIT_WINDOW_MINUTES should be at least 1 minute")

        # Validate CORS settings
        if cls.CORS_ENABLED and not cls.ALLOWED_ORIGINS:
            if cls.ENVIRONMENT == "production":
                errors.append("ALLOWED_ORIGINS must be configured in production when CORS is enabled")
            else:
                logger.warning("ALLOWED_ORIGINS not configured, using localhost defaults")

        # Validate database settings
        if cls.ENVIRONMENT == "production" and cls.DATABASE_SSL_MODE == "disable":
            errors.append("DATABASE_SSL_MODE should not be disabled in production")

        if cls.DATABASE_TIMEOUT < 5:
            errors.append("DATABASE_TIMEOUT should be at least 5 seconds")

        return {
            "errors": errors,
            "warnings": [],
            "settings": {
                "jwt": {
                    "algorithm": cls.JWT_ALGORITHM,
                    "access_token_expire_minutes": cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
                    "refresh_token_expire_days": cls.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
                    "secret_key_set": bool(cls.JWT_SECRET_KEY)
                },
                "password": {
                    "min_length": cls.PASSWORD_MIN_LENGTH,
                    "max_length": cls.PASSWORD_MAX_LENGTH,
                    "bcrypt_rounds": cls.BCRYPT_ROUNDS
                },
                "rate_limiting": {
                    "enabled": cls.RATE_LIMIT_ENABLED,
                    "attempts": cls.RATE_LIMIT_ATTEMPTS,
                    "window_minutes": cls.RATE_LIMIT_WINDOW_MINUTES
                },
                "cors": {
                    "enabled": cls.CORS_ENABLED,
                    "allowed_origins": cls.ALLOWED_ORIGINS,
                    "allowed_methods": cls.ALLOWED_METHODS,
                    "allowed_headers": cls.ALLOWED_HEADERS
                },
                "security_headers": {
                    "enabled": cls.SECURITY_HEADERS_ENABLED,
                    "csp_policy": cls.CSP_POLICY,
                    "hsts_max_age": cls.HSTS_MAX_AGE
                },
                "environment": {
                    "environment": cls.ENVIRONMENT,
                    "debug_mode": cls.DEBUG_MODE,
                    "use_https": cls.USE_HTTPS
                }
            }
        }


class SecurityMonitor:
    """Security monitoring and alerting."""

    def __init__(self):
        self.failed_attempts: Dict[str, int] = {}
        self.suspicious_ips: List[str] = []
        self.security_events: List[Dict[str, Any]] = []

    def log_failed_login(self, ip: str, username: Optional[str] = None) -> None:
        """Log failed login attempt."""

        event = {
            "timestamp": "2026-01-06T10:30:00Z",
            "type": "failed_login",
            "ip": ip,
            "username": username,
            "severity": "medium"
        }

        self.security_events.append(event)
        logger.warning(f"Failed login attempt from {ip} for user {username}")

        # Check for brute force
        if ip in self.failed_attempts:
            self.failed_attempts[ip] += 1
            if self.failed_attempts[ip] >= 5:
                self.suspicious_ips.append(ip)
                logger.critical(f"Brute force attack detected from {ip}")
        else:
            self.failed_attempts[ip] = 1

    def log_suspicious_activity(self, ip: str, activity: str, severity: str = "medium") -> None:
        """Log suspicious activity."""

        event = {
            "timestamp": "2026-01-06T10:30:00Z",
            "type": "suspicious_activity",
            "ip": ip,
            "activity": activity,
            "severity": severity
        }

        self.security_events.append(event)
        logger.warning(f"Suspicious activity from {ip}: {activity}")

    def get_security_report(self) -> Dict[str, Any]:
        """Get security monitoring report."""

        return {
            "failed_login_attempts": self.failed_attempts,
            "suspicious_ips": self.suspicious_ips,
            "recent_events": self.security_events[-10:],  # Last 10 events
            "total_events": len(self.security_events)
        }


# Global security monitor instance
security_monitor = SecurityMonitor()


def get_security_settings() -> Dict[str, Any]:
    """Get validated security settings."""

    validation_result = SecuritySettings.validate_settings()

    if validation_result["errors"]:
        logger.error("Security configuration errors found:")
        for error in validation_result["errors"]:
            logger.error(f"  - {error}")

    return validation_result


def setup_security_logging() -> None:
    """Setup security-focused logging."""

    # Configure logging level
    logging.basicConfig(
        level=getattr(logging, SecuritySettings.LOG_LEVEL.upper()),
        format=SecuritySettings.LOG_FORMAT
    )

    # Security-specific logger configuration
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.WARNING)

    # Add security event handler if needed
    # (In production, this would integrate with SIEM systems)