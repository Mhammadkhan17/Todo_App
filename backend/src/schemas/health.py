#!/usr/bin/env python3
"""
Health Check Schema

Defines health check response model.
"""

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    message: str
    version: str
    database_status: str = "unknown"
    timestamp: str = None