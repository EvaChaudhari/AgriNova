"""Agronomic Crop Knowledge and Variety Schemas (Pydantic v2)."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CropVarietyResponse(BaseModel):
    """Cultivar variety and hybrid characteristics."""

    id: int
    variety_name: str
    duration_days: int
    drought_tolerance: str
    flood_tolerance: str
    potential_yield_q_ha: float

    model_config = ConfigDict(from_attributes=True)


class CropGrowthStageResponse(BaseModel):
    """FAO-56 phenological stage parameters."""

    id: int
    stage_name: str
    start_das: int
    end_das: int
    kc: float
    rooting_depth_m: float
    depletion_fraction_p: float
    ky: float
    critical_water_stage: bool

    model_config = ConfigDict(from_attributes=True)


class CropNutrientBenchmarkResponse(BaseModel):
    """ICAR STCR targeted yield coefficients and maximum recommended chemical doses."""

    stcr_a_n: float
    stcr_b_n: float
    stcr_a_p: float
    stcr_b_p: float
    stcr_a_k: float
    stcr_b_k: float
    max_n_kg_ha: float
    max_p_kg_ha: float
    max_k_kg_ha: float
    target_yield_default_q_ha: float

    model_config = ConfigDict(from_attributes=True)


class CropPestProfileResponse(BaseModel):
    """CIB&RC approved IPM pest and disease guidance."""

    id: int
    pest_name: str
    pest_type: str
    affected_growth_stage: str
    symptoms: str
    economic_threshold_etl: str
    ipm_practice: str
    approved_chemical: Optional[str] = None
    cib_restriction: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CropSummaryResponse(BaseModel):
    """Brief crop listing summary."""

    id: int
    name: str
    scientific_name: str
    season: str
    category: str
    standard_duration_days: int

    model_config = ConfigDict(from_attributes=True)


class CropDetailResponse(BaseModel):
    """Complete crop dossier including varieties, growth stages, STCR formulas, and pest profiles."""

    id: int
    name: str
    scientific_name: str
    season: str
    category: str
    standard_duration_days: int
    varieties: list[CropVarietyResponse] = []
    growth_stages: list[CropGrowthStageResponse] = []
    nutrient_benchmark: Optional[CropNutrientBenchmarkResponse] = None
    pest_profiles: list[CropPestProfileResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StageAtDASResponse(BaseModel):
    """Crop growth stage, active Kc, rooting depth, and pest vulnerabilities for a given Day After Sowing."""

    crop_name: str
    das: int
    current_stage: str
    kc: float
    rooting_depth_m: float
    depletion_fraction_p: float
    ky: float
    critical_water_stage: bool
    days_remaining_in_stage: int
    stage_pest_threats: list[CropPestProfileResponse] = []

