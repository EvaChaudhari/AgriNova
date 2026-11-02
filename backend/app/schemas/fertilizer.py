"""Soil Health Card and ICAR STCR Fertilizer Recommendation Schemas (Pydantic v2)."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SoilHealthCardCreate(BaseModel):
    """Payload to ingest laboratory or farmer Soil Health Card test values."""

    nitrogen_kg_ha: Optional[float] = Field(default=None, ge=0.0, le=1000.0, description="Available Nitrogen in kg/ha")
    phosphorus_kg_ha: Optional[float] = Field(default=None, ge=0.0, le=300.0, description="Available Phosphorus in kg/ha")
    potassium_kg_ha: Optional[float] = Field(default=None, ge=0.0, le=1000.0, description="Available Potassium in kg/ha")
    ph: Optional[float] = Field(default=None, ge=3.0, le=12.0, description="Soil pH value (1:2.5 soil-water suspension)")
    organic_carbon_percent: Optional[float] = Field(default=None, ge=0.0, le=5.0, description="Organic Carbon percentage")
    tested_date: Optional[date] = Field(default=None, description="Date soil sample was tested")
    source_type: str = Field(default="SOIL_HEALTH_CARD_MANUAL", description="Data source indicator")


class NutrientRatingResponse(BaseModel):
    """Qualitative fertility classification and composite Soil Health Index."""

    nitrogen_rating: str  # LOW, MEDIUM, HIGH
    phosphorus_rating: str  # LOW, MEDIUM, HIGH
    potassium_rating: str  # LOW, MEDIUM, HIGH
    organic_carbon_rating: str  # LOW, MEDIUM, HIGH
    ph_classification: str  # ACIDIC, NEUTRAL, ALKALINE, SODIC
    soil_health_index: float  # Composite 0 - 100 score
    soil_amendment_directive: Optional[str] = None


class PlotSoilRatingResponse(BaseModel):
    """Plot soil physicochemical properties and fertility ratings."""

    plot_id: int
    record_id: int
    nitrogen_kg_ha: float
    phosphorus_kg_ha: float
    potassium_kg_ha: float
    ph: float
    organic_carbon_percent: float
    source_type: str
    tested_date: date
    rating: NutrientRatingResponse

    model_config = ConfigDict(from_attributes=True)


class FertilizerRecommendationRequest(BaseModel):
    """Input parameters for targeted yield fertilizer computation."""

    target_yield_q_ha: Optional[float] = Field(default=None, ge=1.0, le=2000.0, description="Target crop yield in quintals/ha")
    crop_name: Optional[str] = Field(default=None, description="Optional override crop name (defaults to active plot cycle)")


class SplitApplicationItemResponse(BaseModel):
    """Stage-wise commercial fertilizer bag application instruction."""

    growth_stage: str
    timing_das: str
    dap_bags: float
    urea_bags: float
    mop_bags: float
    instructions: str


class FertilizerRecommendationResponse(BaseModel):
    """Customized ICAR STCR fertilizer advisory and commercial 50kg bag equivalents."""

    plot_id: int
    crop_name: str
    target_yield_q_ha: float
    recommended_n_kg_ha: float
    recommended_p_kg_ha: float
    recommended_k_kg_ha: float
    is_clamped_to_safe_max: bool
    total_dap_bags_50kg: float
    total_urea_bags_50kg: float
    total_mop_bags_50kg: float
    field_area_hectares: float
    field_total_dap_bags: float
    field_total_urea_bags: float
    field_total_mop_bags: float
    split_schedule: list[SplitApplicationItemResponse] = []
    soil_rating: Optional[NutrientRatingResponse] = None
    advisory_notes: list[str] = []

