#!/usr/bin/env python3
"""
Error Schemas

Pydantic models for error responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Error detail model."""
    type: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: str
    path: str


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    error: str = "Validation Error"
    message: str = "Request validation failed"
    details: List[Dict[str, Any]]
    timestamp: str
    path: str