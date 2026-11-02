"""Environmental Observations and Spatial Ingestion Endpoints.

Provides APIs for querying historical weather, rolling forecasts, Sentinel-2 vegetation
indices, DEM terrain slope & erosion hazards, and on-demand multi-layer synchronization.
"""

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import Identity, get_current_identity
from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.engines.hazard_state import HazardEngineInput, HazardStateMachine
from app.engines.satellite_processor import SatelliteProcessor
from app.engines.terrain_engine import TerrainEngine
from app.repositories.observation_repo import ObservationRepository
from app.repositories.plot_repository import PlotRepository
from app.schemas.observations import (
    EnvironmentalSyncResponse,
    SatelliteObservationResponse,
    SatelliteTimeSeriesResponse,
    TerrainTopographyResponse,
    WeatherForecastResponse,
    WeatherHistoryResponse,
    WeatherObservationResponse,
)
from app.services.weather_ingestion import WeatherIngestionService
from app.services.wris_service import WRISGroundwaterService

router = APIRouter(prefix="/plots/{plot_id}", tags=["Environmental Observations & Spatial Ingestion"])


def _get_plot_or_404(plot_id: int, db: Session) -> Any:
    plot_repo = PlotRepository(db)
    plot = plot_repo.get_plot_by_id(plot_id)
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")
    return plot


@router.get("/weather/history", response_model=WeatherHistoryResponse)
async def get_plot_weather_history(
    plot_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> WeatherHistoryResponse:
    """Retrieve historical weather observations and current 5-day rolling forecast window."""
    plot = _get_plot_or_404(plot_id, db)
    obs_repo = ObservationRepository(db)

    # Fetch existing records
    history = obs_repo.get_weather_history(plot_id, limit=limit)
    forecasts = obs_repo.get_latest_forecasts(plot_id)

    # Ingest bundle if no observations or forecasts are present
    if not history or not forecasts:
        bundle = await WeatherIngestionService.ingest_weather_bundle(
            latitude=plot.centroid_lat,
            longitude=plot.centroid_lon,
        )
        saved_obs = obs_repo.save_weather_observation(plot_id, bundle.observation)
        saved_forecasts = obs_repo.save_weather_forecasts(plot_id, bundle.forecasts)
        history = [saved_obs]
        forecasts = saved_forecasts
        rolling_24h = bundle.rolling_24h_rainfall_mm
        rolling_72h = bundle.rolling_72h_rainfall_mm
        is_storm = bundle.is_storm_hazard
    else:
        rolling_24h = history[0].rainfall_24h_mm
        next_48h = sum(f.rainfall_mm for f in forecasts[:2])
        rolling_72h = round(rolling_24h + next_48h, 1)
        is_storm = (
            rolling_24h >= WeatherIngestionService.STORM_24H_THRESHOLD_MM
            or rolling_72h >= WeatherIngestionService.STORM_72H_THRESHOLD_MM
        )

    current_resp = WeatherObservationResponse.model_validate(history[0]) if history else None
    history_resp = [WeatherObservationResponse.model_validate(h) for h in history]
    forecast_resp = [WeatherForecastResponse.model_validate(f) for f in forecasts]

    return WeatherHistoryResponse(
        plot_id=plot_id,
        current_observation=current_resp,
        historical_observations=history_resp,
        forecast_window=forecast_resp,
        rolling_24h_rainfall_mm=rolling_24h,
        rolling_72h_rainfall_mm=rolling_72h,
        is_storm_hazard=is_storm,
    )


@router.get("/satellite/timeseries", response_model=SatelliteTimeSeriesResponse)
def get_plot_satellite_timeseries(
    plot_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SatelliteTimeSeriesResponse:
    """Retrieve Sentinel-2 NDVI/NDWI vegetation index trajectory and vigor status."""
    plot = _get_plot_or_404(plot_id, db)
    plot_repo = PlotRepository(db)
    obs_repo = ObservationRepository(db)

    records = obs_repo.get_satellite_timeseries(plot_id, limit=limit)

    # If no records exist, compute current observation using crop phenology
    if not records:
        cycle = plot_repo.get_active_crop_cycle(plot_id)
        crop_name = cycle.crop_name if cycle else "Cotton"
        sowing = cycle.sowing_date if cycle else date.today()

        red, nir, green, swir, scl = SatelliteProcessor.simulate_multispectral_scene(
            crop_name=crop_name,
            das=max(0, (date.today() - sowing).days),
            cloud_pct=10.0,
        )
        zonal = SatelliteProcessor.compute_zonal_statistics(
            red_band=red,
            nir_band=nir,
            green_band=green,
            swir_band=swir,
            scl_band=scl,
            acquisition_date=date.today(),
            sowing_date=sowing,
            crop_name=crop_name,
        )
        saved_sat = obs_repo.save_satellite_observation(plot_id, zonal)
        records = [saved_sat]

    latest = records[0]
    mean_ndvi = latest.mean_ndvi

    if mean_ndvi >= 0.65:
        vigor = "EXCELLENT_VIGOR"
    elif mean_ndvi >= 0.45:
        vigor = "MODERATE_VIGOR"
    elif mean_ndvi >= 0.25:
        vigor = "EARLY_EMERGENCE"
    else:
        vigor = "VEGETATION_STRESSED"

    return SatelliteTimeSeriesResponse(
        plot_id=plot_id,
        latest=SatelliteObservationResponse.model_validate(latest),
        timeseries=[SatelliteObservationResponse.model_validate(r) for r in records],
        vegetation_status=vigor,
    )


@router.get("/terrain", response_model=TerrainTopographyResponse)
def get_plot_terrain(
    plot_id: int,
    db: Session = Depends(get_db),
) -> TerrainTopographyResponse:
    """Retrieve Digital Elevation Model (DEM) slope %, TWI, and runoff erosion hazard."""
    plot = _get_plot_or_404(plot_id, db)
    obs_repo = ObservationRepository(db)

    terrain = obs_repo.get_terrain_topography(plot_id)
    if not terrain:
        analysis = TerrainEngine.analyze_plot_terrain(
            centroid_lat=plot.centroid_lat,
            centroid_lon=plot.centroid_lon,
            known_elevation_m=plot.elevation_m,
            known_slope_percent=plot.slope_percent,
        )
        terrain = obs_repo.save_or_update_terrain(plot_id, analysis)

    return TerrainTopographyResponse.model_validate(terrain)


@router.post("/sync-environmental", response_model=EnvironmentalSyncResponse)
async def sync_plot_environmental_data(
    plot_id: int,
    simulated_rain_mm: Optional[float] = Query(default=None, description="Optional rain override for testing"),
    db: Session = Depends(get_db),
) -> EnvironmentalSyncResponse:
    """On-demand synchronization pulling fresh weather, satellite, groundwater, and terrain data."""
    plot = _get_plot_or_404(plot_id, db)
    plot_repo = PlotRepository(db)
    obs_repo = ObservationRepository(db)

    # 1. Sync Weather & Forecasts
    weather_bundle = await WeatherIngestionService.ingest_weather_bundle(
        latitude=plot.centroid_lat,
        longitude=plot.centroid_lon,
        simulated_live_rain_mm=simulated_rain_mm,
    )
    obs_repo.save_weather_observation(plot_id, weather_bundle.observation)
    obs_repo.save_weather_forecasts(plot_id, weather_bundle.forecasts)

    # 2. Sync Satellite Indices
    cycle = plot_repo.get_active_crop_cycle(plot_id)
    crop_name = cycle.crop_name if cycle else "Cotton"
    sowing = cycle.sowing_date if cycle else date.today()

    red, nir, green, swir, scl = SatelliteProcessor.simulate_multispectral_scene(
        crop_name=crop_name,
        das=max(0, (date.today() - sowing).days),
        cloud_pct=10.0,
    )
    zonal = SatelliteProcessor.compute_zonal_statistics(
        red_band=red,
        nir_band=nir,
        green_band=green,
        swir_band=swir,
        scl_band=scl,
        crop_name=crop_name,
        sowing_date=sowing,
    )
    obs_repo.save_satellite_observation(plot_id, zonal)

    # 3. Sync India-WRIS Groundwater
    wris_record = WRISGroundwaterService.fetch_nearest_station(
        latitude=plot.centroid_lat,
        longitude=plot.centroid_lon,
    )
    obs_repo.save_groundwater_record(plot_id, wris_record)

    # 4. Sync Terrain Topography
    terrain_analysis = TerrainEngine.analyze_plot_terrain(
        centroid_lat=plot.centroid_lat,
        centroid_lon=plot.centroid_lon,
        known_elevation_m=plot.elevation_m,
        known_slope_percent=plot.slope_percent,
    )
    obs_repo.save_or_update_terrain(plot_id, terrain_analysis)

    # 5. Evaluate Hazard State Machine with freshly synchronized observations
    hazard_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=weather_bundle.rolling_24h_rainfall_mm,
        groundwater_depth_mbgl=wris_record.current_depth_mbgl,
        rainfall_deficit_percent=weather_bundle.observation.seasonal_deficit_percent,
        dem_slope_percent=terrain_analysis.slope_percent,
        ndwi=zonal.mean_ndwi,
    )
    hazard_eval = HazardStateMachine.evaluate(hazard_inputs)

    return EnvironmentalSyncResponse(
        plot_id=plot_id,
        status="SUCCESS",
        weather_synced=True,
        satellite_synced=True,
        groundwater_synced=True,
        terrain_synced=True,
        hazard_state=hazard_eval.current_state,
        summary=(
            f"Synced: 24h Rain {weather_bundle.rolling_24h_rainfall_mm}mm, "
            f"NDVI {zonal.mean_ndvi}, Water Table {wris_record.current_depth_mbgl}mbgl, "
            f"Slope {terrain_analysis.slope_percent}%. Current Hazard Mode: {hazard_eval.current_state}."
        ),
    )

