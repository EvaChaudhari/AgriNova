"""Crop Knowledge Base API Router.

Provides endpoints to query crops, varieties, FAO-56 phenological growth stages,
and stage-at-DAS phenological state with IPM pest vulnerabilities.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.models.crop_knowledge import Crop
from app.schemas.crop_knowledge import (
    CropDetailResponse,
    CropPestProfileResponse,
    CropSummaryResponse,
    StageAtDASResponse,
)

router = APIRouter(prefix="/crops", tags=["Crop Knowledge Base"])


@router.get("", response_model=list[CropSummaryResponse])
def list_crops(
    season: Optional[str] = Query(None, description="Filter by crop season (e.g. KHARIF, RABI, ZAID)"),
    category: Optional[str] = Query(None, description="Filter by crop category (e.g. CEREAL, FIBRE, PULSE, OILSEED, CASH)"),
    db: Session = Depends(get_db),
) -> list[CropSummaryResponse]:
    """Retrieve catalog of agronomic crops with optional season and category filtering."""
    query = db.query(Crop).filter(Crop.is_active == True)
    if season:
        query = query.filter(Crop.season == season.upper().strip())
    if category:
        query = query.filter(Crop.category == category.upper().strip())
    crops = query.order_by(Crop.id).all()
    return crops


@router.get("/{crop_id}", response_model=CropDetailResponse)
def get_crop_detail(
    crop_id: int,
    db: Session = Depends(get_db),
) -> CropDetailResponse:
    """Retrieve comprehensive crop dossier including varieties, growth stages, STCR coefficients, and pest profiles."""
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise EntityNotFoundError(f"Crop with ID {crop_id} not found.")
    return crop


@router.get("/{crop_id}/stage-at-das", response_model=StageAtDASResponse)
def get_stage_at_das(
    crop_id: int,
    das: int = Query(..., ge=0, le=1000, description="Day After Sowing (DAS)"),
    db: Session = Depends(get_db),
) -> StageAtDASResponse:
    """Resolve phenological growth stage, active FAO-56 Kc, rooting depth, and active pest threats at a specific DAS."""
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise EntityNotFoundError(f"Crop with ID {crop_id} not found.")

    stages = sorted(crop.growth_stages, key=lambda s: s.start_das)
    if not stages:
        raise EntityNotFoundError(f"No growth stages configured for crop '{crop.name}'.")

    # Match stage containing DAS, or clamp to earliest / latest stage
    selected_stage = None
    for stage in stages:
        if stage.start_das <= das <= stage.end_das:
            selected_stage = stage
            break

    if not selected_stage:
        if das < stages[0].start_das:
            selected_stage = stages[0]
        else:
            selected_stage = stages[-1]

    days_remaining = max(0, selected_stage.end_das - das)

    # Filter pest threats for this growth stage or those that affect ALL stages
    pest_threats = [
        p for p in crop.pest_profiles
        if p.affected_growth_stage in (selected_stage.stage_name, "ALL")
    ]

    return StageAtDASResponse(
        crop_name=crop.name,
        das=das,
        current_stage=selected_stage.stage_name,
        kc=selected_stage.kc,
        rooting_depth_m=selected_stage.rooting_depth_m,
        depletion_fraction_p=selected_stage.depletion_fraction_p,
        ky=selected_stage.ky,
        critical_water_stage=selected_stage.critical_water_stage,
        days_remaining_in_stage=days_remaining,
        stage_pest_threats=[CropPestProfileResponse.model_validate(p) for p in pest_threats],
    )

