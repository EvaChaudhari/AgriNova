"""Farmer Consent and Compliance Audit Logging Models.

Maintains immutable audit records for regulatory compliance (Digital Personal Data Protection Act - DPDP)
and tracks explicit farmer consent grants/revocations across agricultural services.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConsentRecord(Base):
    """Explicit farmer consent record for agronomic telemetry and external data sharing."""

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(String(128), nullable=True, index=True)
    purpose = Column(String(64), nullable=False)  # e.g., IRRIGATION_ADVISORY, WEATHER_ALERTS, SOIL_TELEMETRY
    status = Column(String(20), default="GRANTED", nullable=False)  # GRANTED, REVOKED, EXPIRED
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="consents")


class AuditLog(Base):
    """Append-only audit trail recording security, identity, and lifecycle operations."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(String(128), nullable=True, index=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True)
    details = Column(String(1000), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

