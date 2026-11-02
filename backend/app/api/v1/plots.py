"""Farm Plot & Agronomic Telemetry CRUD Endpoints."""

import math
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from shapely.geometry import shape

from app.core.database import get_db
from app.models.profile import DeviceProfile
from app.models.plot import Farm, FarmPlot, CropCycle
from app.models.telemetry import GroundwaterObservation, SoilHealthRecord
from app.schemas.geospatial import (
    PlotCreateRequest,
    PlotResponse,
    CropCycleCreateRequest,
    CropCycleResponse,
    GroundwaterCreateRequest,
    GroundwaterResponse,
    SoilHealthCreateRequest,
    SoilHealthResponse,
)

router = APIRouter(prefix="/plots", tags=["Farm Plots"])


def calculate_polygon_geodesic_area_hectares(poly_shape: Any, center_lat: float) -> float:
    """Calculate physical ground area in hectares from WGS84 degree polygon."""
    deg_area = poly_shape.area
    # Metric conversion based on local latitude
    lat_rad = math.radians(center_lat)
    m2_area = deg_area * 111320.0 * (111320.0 * math.cos(lat_rad))
    ha = m2_area / 10000.0
    return max(0.01, round(ha, 2))


@router.post("", response_model=PlotResponse, status_code=status.HTTP_201_CREATED)
def create_farm_plot(
    payload: PlotCreateRequest,
    db: Session = Depends(get_db),
) -> PlotResponse:
    """Register farm field boundary polygon and auto-derive centroid and surface area."""
    # Verify device exists
    profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == payload.device_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{payload.device_id}' not found. Please onboard first.",
        )

    # Convert GeoJSON coordinates to Shapely geometry
    try:
        geom = shape(payload.boundary.model_dump())
        centroid_lat = round(float(geom.centroid.y), 6)
        centroid_lon = round(float(geom.centroid.x), 6)
        area_ha = calculate_polygon_geodesic_area_hectares(geom, centroid_lat)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid GeoJSON polygon coordinates: {str(e)}",
        )

    # Verify parent farm if specified
    farm = None
    if payload.farm_id is not None:
        farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm holding with ID {payload.farm_id} not found.",
            )

    # Deactivate previous standalone plots only if NOT registering under a multi-plot farm
    if not payload.farm_id:
        db.query(FarmPlot).filter(
            FarmPlot.device_id == payload.device_id,
            FarmPlot.farm_id.is_(None),
        ).update({"is_active": False})

    plot = FarmPlot(
        farm_id=payload.farm_id,
        user_id=farm.user_id if farm else None,
        device_id=payload.device_id,
        name=payload.name,
        survey_number=payload.survey_number,
        khasra_number=payload.khasra_number,
        boundary=geom.wkt,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_hectares=area_ha,
        soil_texture=payload.soil_texture,
        elevation_m=payload.elevation_m,
        slope_percent=payload.slope_percent,
        is_active=True,
    )
    db.add(plot)
    db.commit()
    db.refresh(plot)

    # Recalculate parent farm total area if linked
    if farm:
        active_plots = db.query(FarmPlot).filter(FarmPlot.farm_id == farm.id, FarmPlot.is_active.is_(True)).all()
        farm.total_area_hectares = round(sum(p.area_hectares for p in active_plots), 2)
        db.commit()

    return PlotResponse.model_validate(plot)


@router.get("", response_model=list[PlotResponse])
def list_farm_plots(
    device_id: Optional[str] = Query(None, description="Hardware device identifier"),
    farm_id: Optional[int] = Query(None, description="Parent farm holding identifier"),
    db: Session = Depends(get_db),
) -> list[PlotResponse]:
    """Retrieve all registered plots for a device or parent farm holding."""
    query = db.query(FarmPlot)
    if farm_id is not None:
        query = query.filter(FarmPlot.farm_id == farm_id)
    elif device_id:
        query = query.filter(FarmPlot.device_id == device_id)
    else:
        return []

    plots = query.order_by(FarmPlot.id.desc()).all()
    return [PlotResponse.model_validate(p) for p in plots]


@router.get("/{plot_id}", response_model=PlotResponse)
def get_plot_details(
    plot_id: int,
    db: Session = Depends(get_db),
) -> PlotResponse:
    """Retrieve single plot metadata."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found")
    return PlotResponse.model_validate(plot)


@router.post("/{plot_id}/crop-cycle", response_model=CropCycleResponse, status_code=status.HTTP_201_CREATED)
def register_crop_cycle(
    plot_id: int,
    payload: CropCycleCreateRequest,
    db: Session = Depends(get_db),
) -> CropCycleResponse:
    """Register active crop cycle for a farm plot."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found")

    # Set previous cycles for this plot to inactive
    db.query(CropCycle).filter(CropCycle.plot_id == plot_id).update({"is_active": False})

    cycle = CropCycle(
        plot_id=plot_id,
        crop_name=payload.crop_name,
        variety=payload.variety,
        sowing_date=payload.sowing_date,
        growth_stage=payload.growth_stage,
        irrigation_method=payload.irrigation_method,
        expected_harvest_date=payload.expected_harvest_date,
        is_active=True,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return CropCycleResponse.model_validate(cycle)


@router.post("/{plot_id}/groundwater", response_model=GroundwaterResponse, status_code=status.HTTP_201_CREATED)
def add_groundwater_observation(
    plot_id: int,
    payload: GroundwaterCreateRequest,
    db: Session = Depends(get_db),
) -> GroundwaterResponse:
    """Record physical groundwater observation (telemetry or WRIS)."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found")

    obs = GroundwaterObservation(
        plot_id=plot_id,
        depth_mbgl=payload.depth_mbgl,
        source_type=payload.source_type,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return GroundwaterResponse.model_validate(obs)


@router.post("/{plot_id}/soil-health", response_model=SoilHealthResponse, status_code=status.HTTP_201_CREATED)
def add_soil_health_record(
    plot_id: int,
    payload: SoilHealthCreateRequest,
    db: Session = Depends(get_db),
) -> SoilHealthResponse:
    """Record Soil Health Card (SHC) physicochemical parameters."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot not found")

    shc = SoilHealthRecord(
        plot_id=plot_id,
        nitrogen_kg_ha=payload.nitrogen_kg_ha,
        phosphorus_kg_ha=payload.phosphorus_kg_ha,
        potassium_kg_ha=payload.potassium_kg_ha,
        ph=payload.ph,
        organic_carbon_percent=payload.organic_carbon_percent,
        source_type=payload.source_type,
    )
    db.add(shc)
    db.commit()
    db.refresh(shc)
    return SoilHealthResponse.model_validate(shc)

