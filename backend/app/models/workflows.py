"""Agronomic Workflow Models (Milestone E).

Implements database-backed persistent entities for:
- Crop Suitability Planning (`crop_plans`)
- Crop-Cycle Roadmaps & Stage Checkpoints (`crop_roadmaps`, `roadmap_checkpoints`)
- Offline Synchronization Audit Trail (`offline_sync_events`)
- Farmer Notifications & Action Alerts (`farmer_notifications`)
- ICAR Approved Agronomic Knowledge Cards for RAG Grounding (`approved_agronomic_guides`)
"""

from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class CropPlan(Base):
    """Multi-criteria crop suitability evaluation and farmer selection."""

    __tablename__ = "crop_plans"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    season = Column(String(32), nullable=False)  # KHARIF, RABI, ZAID
    target_year = Column(Integer, nullable=False, default=lambda: datetime.now(timezone.utc).year)
    rankings_json = Column(Text, nullable=False)  # JSON serialized list of scored candidate crops
    selected_crop = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    plot = relationship("FarmPlot", backref="crop_plans")


class CropRoadmap(Base):
    """End-to-end agronomic milestone calendar for an active crop cycle."""

    __tablename__ = "crop_roadmaps"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_cycle_id = Column(Integer, ForeignKey("crop_cycles.id", ondelete="CASCADE"), nullable=True, index=True)
    crop_name = Column(String(80), nullable=False)
    variety_name = Column(String(120), nullable=True)
    sowing_date = Column(Date, nullable=False)
    expected_harvest_date = Column(Date, nullable=False)
    current_stage = Column(String(64), nullable=False, default="INITIAL")
    total_checkpoints = Column(Integer, nullable=False, default=6)
    completed_checkpoints = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    plot = relationship("FarmPlot", backref="roadmaps")
    crop_cycle = relationship("CropCycle", backref="roadmap")
    checkpoints = relationship(
        "RoadmapCheckpoint",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapCheckpoint.target_day_after_sowing",
    )


class RoadmapCheckpoint(Base):
    """Specific agronomic milestone, intervention window, and completion status."""

    __tablename__ = "roadmap_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("crop_roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(64), nullable=False)  # SOWING, BASAL_FERTILIZATION, WEEDING, etc.
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    target_day_after_sowing = Column(Integer, nullable=False)
    target_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")  # PENDING, COMPLETED, DEFERRED
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    actionable_guidance = Column(Text, nullable=True)

    roadmap = relationship("CropRoadmap", back_populates="checkpoints")


class OfflineSyncEvent(Base):
    """Idempotent audit record tracking client-side queued mutations."""

    __tablename__ = "offline_sync_events"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)  # CHECKPOINT_COMPLETE, LOG_IRRIGATION, OFFLINE_NOTE, etc.
    payload_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="APPLIED")  # APPLIED, DUPLICATE_SKIPPED, CONFLICT_RESOLVED
    server_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    client_timestamp = Column(DateTime, nullable=False)


class FarmerNotification(Base):
    """Actionable agronomic and hazard alert delivered to smallholder farmers."""

    __tablename__ = "farmer_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="SET NULL"), nullable=True, index=True)
    notification_type = Column(String(64), nullable=False)  # WEATHER_HAZARD, IRRIGATION_DUE, ROADMAP_CHECKPOINT, PEST_ALERT
    priority = Column(String(32), nullable=False, default="ROUTINE")  # URGENT, HIGH, ROUTINE
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default="hi")  # hi, mr, te, en
    channel = Column(String(32), nullable=False, default="IN_APP")  # IN_APP, SMS, WHATSAPP
    is_read = Column(Boolean, nullable=False, default=False)
    action_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = Column(DateTime, nullable=True)

    plot = relationship("FarmPlot", backref="notifications")


class ApprovedAgronomicGuide(Base):
    """Standardized ICAR / SAU Package of Practices knowledge cards for RAG grounding."""

    __tablename__ = "approved_agronomic_guides"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_name = Column(String(80), nullable=False, index=True)
    category = Column(String(64), nullable=False)  # SOIL_PREPARATION, SOWING_SPACING, NUTRIENT_MANAGEMENT, IPM_DISEASE_PEST
    stage_name = Column(String(64), nullable=True)
    icar_recommendation = Column(Text, nullable=False)
    citation_source = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

