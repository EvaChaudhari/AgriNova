"""Farmer Identity and Device Session Models.

Supports dual-mode identity: registered farmer User profile (with PIN/phone authentication)
and hardware Device binding.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """Registered farmer identity with encrypted PIN and multi-device association."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    hashed_pin = Column(String(256), nullable=False)
    preferred_language = Column(String(10), default="hi", nullable=False)
    kisan_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    farms = relationship("Farm", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class Device(Base):
    """Physical hardware device binding tracking app installation and active sessions."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    device_id = Column(String(128), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    device_model = Column(String(120), nullable=True)
    os_version = Column(String(64), nullable=True)
    app_version = Column(String(64), nullable=True)
    last_active_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="devices")

