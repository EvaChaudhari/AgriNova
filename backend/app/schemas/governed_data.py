"""DPDP-Compliant Governed Data Product Schemas (Pydantic v2).

Defines aggregated, de-identified data payloads for:
- Farmer Producer Organizations (FPO) collective acreage reporting
- Parametric crop insurance drought & flood trigger indices
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class FPOCropAcreageItem(BaseModel):
    """Aggregated acreage and plot count for a specific crop cultivar."""

    crop_name: str
    variety: Optional[str] = None
    total_plots: int
    total_area_hectares: float
    average_plot_size_ha: float
    active_farmers_count: int


class FPOCropSummaryReport(BaseModel):
    """De-identified district-level collective crop acreage report."""

    district: str
    reporting_period: str
    total_consented_plots: int
    total_consented_acreage_ha: float
    crops: list[FPOCropAcreageItem] = Field(default_factory=list)
    data_anonymization_standard: str = "DPDP-2023 Compliant K-Anonymity (PII Redacted)"
    generated_at: datetime


class ParametricBlockDroughtItem(BaseModel):
    """Administrative block-level drought and moisture stress indicators."""

    block_name: str
    district: str
    normal_rainfall_mm: float
    measured_rainfall_mm: float
    rainfall_deficit_percent: float
    mean_ndwi_moisture_index: float
    groundwater_depth_mbgl: float
    drought_risk_score: float = Field(..., ge=0.0, le=100.0)
    drought_trigger_status: str  # NORMAL, WATCH, TRIGGER_PAYOUT


class ParametricInsuranceIndexReport(BaseModel):
    """Institutional parametric drought index report for claim underwriting."""

    reporting_region: str
    evaluation_season: str
    blocks: list[ParametricBlockDroughtItem] = Field(default_factory=list)
    payout_triggered_blocks_count: int
    data_anonymization_standard: str = "Aggregated Spatial Index (Zero Individual Land Parcel Disclosure)"
    generated_at: datetime

