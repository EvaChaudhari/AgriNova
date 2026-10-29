"""Device Profile model.

Enforces strictly one profile per hardware device_id (single-tenant per device).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class DeviceProfile(Base):
    __tablename__ = "device_profiles"

    device_id = Column(String(128), primary_key=True, index=True)
    farmer_name = Column(String(120), nullable=False)
    preferred_language = Column(String(10), nullable=False, default="hi")
    phone_number = Column(String(20), nullable=True)
    kisan_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    plots = relationship("FarmPlot", back_populates="device", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="device", cascade="all, delete-orphan")

