"""Agronomic Workflow Schemas (Pydantic v2).

Defines request and response schemas for:
- Crop Planner Recommendations
- Crop-Cycle Roadmaps & Stage Checkpoints
- Offline Synchronization Batches
- Farmer Notification Alerts
- Approved Agronomic Guidance Cards
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Crop Suitability Planner
# ============================================================================

class CropSuitabilityItem(BaseModel):
    """Scored and ranked candidate crop suitability evaluation."""

    crop_name: str
    scientific_name: str
    season: str
    category: str
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="Overall suitability index (0-100%)")
    risk_category: str = Field(..., description="OPTIMAL, SUITABLE_WITH_IRRIGATION, or HIGH_RISK_DROUGHT")
    water_access_score: float = Field(..., ge=0.0, le=100.0)
    soil_compatibility_score: float = Field(..., ge=0.0, le=100.0)
    expected_duration_days: int
    limiting_factors: list[str] = Field(default_factory=list)
    recommended_varieties: list[str] = Field(default_factory=list)
    rationale: str


class CropRecommendationRequest(BaseModel):
    """Payload to compute suitability rankings for a plot."""

    plot_id: int
    season: Optional[str] = Field(default=None, description="Target season: KHARIF, RABI, ZAID (auto-detected if omitted)")
    preferred_category: Optional[str] = Field(default=None, description="Optional category filter: CEREAL, PULSE, FIBRE, OILSEED, CASH")


class CropRecommendationResponse(BaseModel):
    """Suitability assessment and ranked crop recommendations."""

    plot_id: int
    season: str
    soil_texture: str
    soil_ph: float
    groundwater_depth_mbgl: float
    irrigation_method: str
    recommendations: list[CropSuitabilityItem] = Field(default_factory=list)


# ============================================================================
# Crop Roadmaps & Checkpoints
# ============================================================================

class RoadmapCheckpointResponse(BaseModel):
    """Individual agronomic milestone checkpoint."""

    id: int
    roadmap_id: int
    stage_name: str
    title: str
    description: str
    target_day_after_sowing: int
    target_date: date
    status: str
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    actionable_guidance: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CheckpointCompleteRequest(BaseModel):
    """Payload to mark a milestone checkpoint completed or deferred."""

    notes: Optional[str] = Field(default=None, description="Farmer field observations or intervention notes")
    status: str = Field(default="COMPLETED", description="COMPLETED or DEFERRED")


class CropRoadmapResponse(BaseModel):
    """Comprehensive crop-cycle roadmap and stage checkpoint timeline."""

    id: int
    plot_id: int
    crop_cycle_id: Optional[int] = None
    crop_name: str
    variety_name: Optional[str] = None
    sowing_date: date
    expected_harvest_date: date
    current_stage: str
    days_after_sowing: int
    total_checkpoints: int
    completed_checkpoints: int
    progress_percent: float
    checkpoints: list[RoadmapCheckpointResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Offline Synchronization
# ============================================================================

class SyncActionItem(BaseModel):
    """Single queued client mutation from offline rural mobile devices."""

    idempotency_key: str = Field(..., description="Client-generated UUID idempotency key")
    action_type: str = Field(..., description="Action type: CHECKPOINT_COMPLETE, LOG_IRRIGATION, OFFLINE_NOTE")
    client_timestamp: datetime = Field(..., description="Timestamp action was created offline")
    payload: dict[str, Any] = Field(default_factory=dict, description="Action specific parameters")


class SyncBatchRequest(BaseModel):
    """Batch of queued offline actions submitted when connectivity resumes."""

    device_id: str
    actions: list[SyncActionItem] = Field(default_factory=list)


class SyncActionResult(BaseModel):
    """Result of processing an individual sync action."""

    idempotency_key: str
    action_type: str
    status: str  # APPLIED, DUPLICATE_SKIPPED, ERROR
    message: str


class SyncBatchResponse(BaseModel):
    """Summary of batch synchronization execution."""

    device_id: str
    total_actions: int
    applied: int
    skipped: int
    results: list[SyncActionResult] = Field(default_factory=list)
    server_timestamp: datetime


# ============================================================================
# Farmer Notifications
# ============================================================================

class NotificationResponse(BaseModel):
    """Farmer alert item with priority and delivery channel."""

    id: int
    device_id: str
    plot_id: Optional[int] = None
    notification_type: str
    priority: str
    title: str
    body: str
    language: str
    channel: str
    is_read: bool
    action_url: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationReadResponse(BaseModel):
    """Notification acknowledgment confirmation."""

    id: int
    is_read: bool
    acknowledged_at: datetime


# ============================================================================
# Approved Knowledge Guidance (RAG)
# ============================================================================

class AgronomicGuideResponse(BaseModel):
    """Vetted ICAR / State Agricultural University package of practices card."""

    id: int
    crop_name: str
    category: str
    stage_name: Optional[str] = None
    icar_recommendation: str
    citation_source: str

    model_config = ConfigDict(from_attributes=True)

