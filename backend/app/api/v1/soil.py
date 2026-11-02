"""Soil Intelligence & ICAR STCR Fertilizer Recommendation API Router.

Provides endpoints to ingest Soil Health Card test values, evaluate qualitative
fertility ratings and Soil Health Index, and compute commercial fertilizer bag schedules.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.engines.fertilizer_engine import FertilizerEngine
from app.models.crop_knowledge import Crop
from app.models.plot import CropCycle, FarmPlot
from app.schemas.fertilizer import (
    FertilizerRecommendationRequest,
    FertilizerRecommendationResponse,
    NutrientRatingResponse,
    PlotSoilRatingResponse,
    SoilHealthCardCreate,
    SplitApplicationItemResponse,
)
from app.services.soil_ingestion_service import SoilIngestionService

router = APIRouter(prefix="/plots", tags=["Soil Intelligence & Fertilizer Recommendations"])


@router.post("/{plot_id}/soil", response_model=PlotSoilRatingResponse, status_code=status.HTTP_201_CREATED)
def ingest_plot_soil_health(
    plot_id: int,
    payload: SoilHealthCardCreate,
    db: Session = Depends(get_db),
) -> PlotSoilRatingResponse:
    """Ingest Soil Health Card lab measurements for a plot and return ICAR fertility ratings."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")

    record, rating = SoilIngestionService.ingest_soil_record(
        db=db,
        plot_id=plot_id,
        nitrogen_kg_ha=payload.nitrogen_kg_ha,
        phosphorus_kg_ha=payload.phosphorus_kg_ha,
        potassium_kg_ha=payload.potassium_kg_ha,
        ph=payload.ph,
        organic_carbon_percent=payload.organic_carbon_percent,
        source_type=payload.source_type,
        tested_date=payload.tested_date,
    )

    return PlotSoilRatingResponse(
        plot_id=record.plot_id,
        record_id=record.id,
        nitrogen_kg_ha=record.nitrogen_kg_ha,
        phosphorus_kg_ha=record.phosphorus_kg_ha,
        potassium_kg_ha=record.potassium_kg_ha,
        ph=record.ph,
        organic_carbon_percent=record.organic_carbon_percent,
        source_type=record.source_type,
        tested_date=record.tested_date,
        rating=NutrientRatingResponse(
            nitrogen_rating=rating.nitrogen_rating,
            phosphorus_rating=rating.phosphorus_rating,
            potassium_rating=rating.potassium_rating,
            organic_carbon_rating=rating.organic_carbon_rating,
            ph_classification=rating.ph_classification,
            soil_health_index=rating.soil_health_index,
            soil_amendment_directive=rating.soil_amendment_directive,
        ),
    )


@router.get("/{plot_id}/soil/rating", response_model=PlotSoilRatingResponse)
def get_plot_soil_rating(
    plot_id: int,
    db: Session = Depends(get_db),
) -> PlotSoilRatingResponse:
    """Retrieve qualitative soil fertility tiers, Soil Health Index (0-100), and soil amendments for a plot."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")

    record, rating = SoilIngestionService.get_latest_soil_rating(db=db, plot_id=plot_id)

    return PlotSoilRatingResponse(
        plot_id=record.plot_id,
        record_id=record.id,
        nitrogen_kg_ha=record.nitrogen_kg_ha,
        phosphorus_kg_ha=record.phosphorus_kg_ha,
        potassium_kg_ha=record.potassium_kg_ha,
        ph=record.ph,
        organic_carbon_percent=record.organic_carbon_percent,
        source_type=record.source_type,
        tested_date=record.tested_date,
        rating=NutrientRatingResponse(
            nitrogen_rating=rating.nitrogen_rating,
            phosphorus_rating=rating.phosphorus_rating,
            potassium_rating=rating.potassium_rating,
            organic_carbon_rating=rating.organic_carbon_rating,
            ph_classification=rating.ph_classification,
            soil_health_index=rating.soil_health_index,
            soil_amendment_directive=rating.soil_amendment_directive,
        ),
    )


@router.post("/{plot_id}/fertilizer-recommendation", response_model=FertilizerRecommendationResponse)
def compute_fertilizer_recommendation(
    plot_id: int,
    payload: FertilizerRecommendationRequest,
    db: Session = Depends(get_db),
) -> FertilizerRecommendationResponse:
    """Compute customized ICAR STCR targeted yield fertilizer advisory and commercial 50kg bag equivalents."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")

    # Determine target crop
    target_crop_name = payload.crop_name
    if not target_crop_name:
        active_cycle = db.query(CropCycle).filter(CropCycle.plot_id == plot_id, CropCycle.is_active == True).first()
        target_crop_name = active_cycle.crop_name if active_cycle else "Cotton"

    # Query Crop agronomic benchmark
    crop = db.query(Crop).filter(Crop.name.ilike(target_crop_name)).first()
    if crop and crop.nutrient_benchmark:
        bm = crop.nutrient_benchmark
        stcr_coeffs = {
            "stcr_a_n": bm.stcr_a_n,
            "stcr_b_n": bm.stcr_b_n,
            "stcr_a_p": bm.stcr_a_p,
            "stcr_b_p": bm.stcr_b_p,
            "stcr_a_k": bm.stcr_a_k,
            "stcr_b_k": bm.stcr_b_k,
        }
        max_bounds = {
            "max_n_kg_ha": bm.max_n_kg_ha,
            "max_p_kg_ha": bm.max_p_kg_ha,
            "max_k_kg_ha": bm.max_k_kg_ha,
        }
        target_yield = payload.target_yield_q_ha or bm.target_yield_default_q_ha
        crop_display_name = crop.name
    else:
        # Fallback STCR coefficients if crop not found in knowledge base
        stcr_coeffs = {
            "stcr_a_n": 4.40,
            "stcr_b_n": 0.38,
            "stcr_a_p": 1.80,
            "stcr_b_p": 0.45,
            "stcr_a_k": 2.10,
            "stcr_b_k": 0.18,
        }
        max_bounds = {
            "max_n_kg_ha": 150.0,
            "max_p_kg_ha": 75.0,
            "max_k_kg_ha": 75.0,
        }
        target_yield = payload.target_yield_q_ha or 25.0
        crop_display_name = target_crop_name

    # Retrieve plot soil health test values
    record, rating = SoilIngestionService.get_latest_soil_rating(db=db, plot_id=plot_id)

    # Compute STCR fertilizer requirement
    result = FertilizerEngine.calculate_stcr_fertilizer(
        crop_name=crop_display_name,
        target_yield_q_ha=target_yield,
        soil_n_kg_ha=record.nitrogen_kg_ha,
        soil_p_kg_ha=record.phosphorus_kg_ha,
        soil_k_kg_ha=record.potassium_kg_ha,
        stcr_coeffs=stcr_coeffs,
        max_bounds=max_bounds,
        field_area_ha=plot.area_hectares,
        soil_ph=record.ph,
        organic_carbon_pct=record.organic_carbon_percent,
    )

    return FertilizerRecommendationResponse(
        plot_id=plot_id,
        crop_name=result.crop_name,
        target_yield_q_ha=result.target_yield_q_ha,
        recommended_n_kg_ha=result.recommended_n_kg_ha,
        recommended_p_kg_ha=result.recommended_p_kg_ha,
        recommended_k_kg_ha=result.recommended_k_kg_ha,
        is_clamped_to_safe_max=result.is_clamped_to_safe_max,
        total_dap_bags_50kg=result.total_dap_bags_50kg,
        total_urea_bags_50kg=result.total_urea_bags_50kg,
        total_mop_bags_50kg=result.total_mop_bags_50kg,
        field_area_hectares=result.field_area_hectares,
        field_total_dap_bags=result.field_total_dap_bags,
        field_total_urea_bags=result.field_total_urea_bags,
        field_total_mop_bags=result.field_total_mop_bags,
        split_schedule=[
            SplitApplicationItemResponse(
                growth_stage=item.growth_stage,
                timing_das=item.timing_das,
                dap_bags=item.dap_bags,
                urea_bags=item.urea_bags,
                mop_bags=item.mop_bags,
                instructions=item.instructions,
            )
            for item in result.split_schedule
        ],
        soil_rating=NutrientRatingResponse(
            nitrogen_rating=rating.nitrogen_rating,
            phosphorus_rating=rating.phosphorus_rating,
            potassium_rating=rating.potassium_rating,
            organic_carbon_rating=rating.organic_carbon_rating,
            ph_classification=rating.ph_classification,
            soil_health_index=rating.soil_health_index,
            soil_amendment_directive=rating.soil_amendment_directive,
        ),
        advisory_notes=result.advisory_notes,
    )

