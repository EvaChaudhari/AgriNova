"""Shared Common Schemas & Contracts (M01).

Defines reusable Pydantic v2 schemas for RFC 7807 problem details,
observation provenance metadata, and generic paginated envelopes.
"""

from datetime import datetime, timezone
from typing import Any, Generic, Literal, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

QualityStatus = Literal["MEASURED", "FORECAST", "DERIVED", "ESTIMATED", "SYNTHETIC_FALLBACK"]


class ProvenanceMetadata(BaseModel):
    """Provenance and data-quality metadata for agricultural observations."""

    source: str = Field(..., description="Ingestion source (e.g. SENSOR, IMD, WRIS, SHC, STAC, FALLBACK)")
    quality_status: QualityStatus = Field(..., description="Scientific quality status")
    observation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Physical time the event occurred in the field",
    )
    retrieval_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the observation was ingested into AgriNova",
    )
    unit: str = Field(..., description="Physical measurement unit (e.g. mm, C, mbgl, kg/ha)")
    uncertainty: Optional[float] = Field(default=None, description="Estimated measurement uncertainty or standard error")
    fallback_used: bool = Field(default=False, description="Whether fallback baseline was substituted")

    model_config = ConfigDict(from_attributes=True)


class StandardObservationEnvelope(BaseModel, Generic[T]):
    """Standardized wrapper for any agricultural observation with complete provenance."""

    parameter: str = Field(..., description="Agronomic parameter name")
    value: T = Field(..., description="Observed or derived value")
    provenance: ProvenanceMetadata = Field(..., description="Quality and lineage metadata")

    model_config = ConfigDict(from_attributes=True)


class InvalidParam(BaseModel):
    """Field-level validation error representation."""

    name: str = Field(..., description="Field path or parameter name")
    reason: str = Field(..., description="Validation failure explanation")
    type: Optional[str] = Field(default=None, description="Validation constraint type")


class ProblemDetails(BaseModel):
    """RFC 7807 compliant problem details representation."""

    type: str = Field(..., description="URI identifier for problem type")
    title: str = Field(..., description="Short, human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation of error")
    instance: str = Field(..., description="URI of the request path")
    correlation_id: str = Field(..., description="Correlation ID for server diagnostics")
    invalid_params: Optional[list[InvalidParam]] = Field(default=None, description="Field validation errors")

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope."""

    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page limit")
    items: list[T] = Field(default_factory=list, description="Page items")

    model_config = ConfigDict(from_attributes=True)

