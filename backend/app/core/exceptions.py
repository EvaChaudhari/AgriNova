"""Krishi Mitra / AgriNova Centralized Domain Exceptions & RFC 7807 Problem Details.

Provides unified error definitions and RFC 7807 compliant JSON response formatting.
Ensures zero internal stack traces or database connection details leak to clients.
"""

from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AgriNovaException(Exception):
    """Base exception for all agricultural platform domain and infrastructure errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        title: Optional[str] = None,
        invalid_params: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        if title is not None:
            self.title = title
        self.invalid_params = invalid_params or []


class EntityNotFoundError(AgriNovaException):
    """Raised when a requested resource (farmer, plot, session) does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    title = "Resource Not Found"


class ValidationError(AgriNovaException):
    """Raised when business logic or input validation constraints fail."""

    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    error_code = "VALIDATION_ERROR"
    title = "Validation Failed"


class UnauthorizedAccessError(AgriNovaException):
    """Raised when authentication credentials or token are invalid or missing."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    title = "Authentication Required"


class ForbiddenActionError(AgriNovaException):
    """Raised when authenticated user lacks permission for the resource."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    title = "Access Forbidden"


class HydrologicalCalculationError(AgriNovaException):
    """Raised when FAO-56 Penman-Monteith physical equations fail or inputs are invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "HYDROLOGY_CALCULATION_ERROR"
    title = "Hydrological Calculation Error"


class HazardStateViolationError(AgriNovaException):
    """Raised when an operation violates active hazard safety restrictions."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "HAZARD_STATE_VIOLATION"
    title = "Hazard Safety Restriction Violation"


class DatabaseConnectionError(AgriNovaException):
    """Raised when database connectivity cannot be established or verified."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATABASE_UNAVAILABLE"
    title = "Database Connection Unavailable"


class StorageUnavailableError(AgriNovaException):
    """Raised when local or remote storage backend is inaccessible or read-only."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "STORAGE_UNAVAILABLE"
    title = "Storage Backend Unavailable"


class RateLimitExceededError(AgriNovaException):
    """Raised when client exceeds sliding-window request rate limit."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    title = "Too Many Requests"

    def __init__(self, detail: str = "Rate limit exceeded. Please slow down.", retry_after: int = 60) -> None:
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS, error_code="RATE_LIMIT_EXCEEDED", title="Too Many Requests")
        self.retry_after = retry_after


def build_problem_details_response(
    status_code: int,
    title: str,
    detail: str,
    error_code: str,
    instance: str,
    correlation_id: str,
    invalid_params: Optional[list[dict[str, Any]]] = None,
    headers: Optional[dict[str, str]] = None,
) -> JSONResponse:
    """Build an RFC 7807 compliant problem details response."""
    error_type = f"urn:agrinova:error:{error_code.lower().replace('_', '-')}"
    content: dict[str, Any] = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "correlation_id": correlation_id,
    }
    if invalid_params:
        content["invalid_params"] = invalid_params

    resp_headers = {"X-Correlation-ID": correlation_id}
    if headers:
        resp_headers.update(headers)

    return JSONResponse(
        status_code=status_code,
        content=content,
        media_type="application/problem+json",
        headers=resp_headers,
    )
