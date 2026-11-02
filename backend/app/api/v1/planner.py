"""Crop Suitability Planner API Router.

Provides multi-criteria crop selection recommendations based on soil texture,
soil pH, regional groundwater table, and irrigation infrastructure.
"""

from datetime import datetime, timezone
import json
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.engines.crop_planner import CropPlannerEngine
from app.models.plot import CropCycle, FarmPlot
from app.models.telemetry import GroundwaterObservation, SoilHealthRecord
from app.models.workflows import CropPlan
from app.schemas.workflows import (
    CropRecommendationRequest,
    CropRecommendationResponse,
)

router = APIRouter(prefix="/planner", tags=["Crop Planner"])


def _detect_current_season() -> str:
    """Infer agricultural season from current calendar month in India."""
    m = datetime.now(timezone.utc).month
    if 6 <= m <= 10:
        return "KHARIF"
    elif 11 <= m or m <= 2:
        return "RABI"
    else:
        return "ZAID"


@router.post("/recommend-crops", response_model=CropRecommendationResponse)
def recommend_crops_for_plot(
    payload: CropRecommendationRequest,
    db: Session = Depends(get_db),
) -> CropRecommendationResponse:
    """Evaluate multi-criteria crop suitability for a plot and return ranked recommendations."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == payload.plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {payload.plot_id} not found.")

    # 1. Resolve soil properties
    soil_texture = plot.soil_texture or "Vertisol"
    latest_soil = (
        db.query(SoilHealthRecord)
        .filter(SoilHealthRecord.plot_id == plot.id)
        .order_by(SoilHealthRecord.tested_date.desc(), SoilHealthRecord.id.desc())
        .first()
    )
    soil_ph = latest_soil.ph if latest_soil else 7.5

    # 2. Resolve groundwater depth
    latest_gw = (
        db.query(GroundwaterObservation)
        .filter(GroundwaterObservation.plot_id == plot.id)
        .order_by(GroundwaterObservation.observation_date.desc(), GroundwaterObservation.id.desc())
        .first()
    )
    gw_depth = latest_gw.depth_mbgl if latest_gw else 12.0

    # 3. Resolve irrigation method from active cycle
    active_cycle = (
        db.query(CropCycle)
        .filter(CropCycle.plot_id == plot.id, CropCycle.is_active == True)
        .first()
    )
    irrigation_method = active_cycle.irrigation_method if active_cycle else "DRIP"

    # 4. Resolve season
    target_season = payload.season or _detect_current_season()

    # 5. Execute Multi-criteria scoring
    recommendations = CropPlannerEngine.evaluate_crop_suitability(
        db=db,
        soil_texture=soil_texture,
        soil_ph=soil_ph,
        groundwater_depth_mbgl=gw_depth,
        irrigation_method=irrigation_method,
        season=target_season,
        preferred_category=payload.preferred_category,
    )

    # 6. Audit in crop_plans table
    plan = CropPlan(
        plot_id=plot.id,
        season=target_season,
        target_year=datetime.now(timezone.utc).year,
        rankings_json=json.dumps([r.model_dump() for r in recommendations]),
        selected_crop=recommendations[0].crop_name if recommendations else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(plan)
    db.commit()

    return CropRecommendationResponse(
        plot_id=plot.id,
        season=target_season,
        soil_texture=soil_texture,
        soil_ph=soil_ph,
        groundwater_depth_mbgl=gw_depth,
        irrigation_method=irrigation_method,
        recommendations=recommendations,
    )

