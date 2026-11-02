"""Farmer Consent and Compliance Audit Logging Schemas (Pydantic v2)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


VALID_CONSENT_PURPOSES = {
    "IRRIGATION_ADVISORY",
    "WEATHER_ALERTS",
    "SOIL_TELEMETRY",
    "SATELLITE_ANALYTICS",
    "GOVERNMENT_SCHEMES",
}


class ConsentGrantRequest(BaseModel):
    """Payload to explicitly grant consent for an agronomic or analytical purpose."""

    purpose: str = Field(..., description="Agro-analytical consent purpose")
    device_id: Optional[str] = Field(default=None, description="Optional hardware device context")


class ConsentRevokeRequest(BaseModel):
    """Payload to explicitly revoke previously granted consent."""

    purpose: str = Field(..., description="Agro-analytical consent purpose to revoke")
    device_id: Optional[str] = Field(default=None, description="Optional hardware device context")


class ConsentResponse(BaseModel):
    """Farmer consent record details."""

    id: int
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    purpose: str
    status: str  # GRANTED, REVOKED, EXPIRED
    granted_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentStatusResponse(BaseModel):
    """Aggregated consent status map and underlying records."""

    purposes: dict[str, bool]
    records: list[ConsentResponse]


class AuditLogResponse(BaseModel):
    """Regulatory and security audit trail record."""

    id: int
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

