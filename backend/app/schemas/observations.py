"""Environmental Observations and Spatial Ingestion Schemas (Pydantic v2)."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WeatherObservationResponse(BaseModel):
    """Historical or real-time meteorological observation."""

    id: int
    plot_id: int
    observation_time: datetime
    temp_min_c: float
    temp_max_c: float
    temp_mean_c: float
    relative_humidity_percent: float
    wind_speed_2m_mps: float
    solar_radiation_mj_m2: float
    rainfall_24h_mm: float
    source: str
    provenance_type: str
    quality_score: float

    model_config = ConfigDict(from_attributes=True)


class WeatherForecastResponse(BaseModel):
    """Daily forecast metrics for rolling window."""

    forecast_date: date
    temp_min_c: float
    temp_max_c: float
    rainfall_mm: float
    precipitation_probability: float
    condition_code: str
    condition_description: str

    model_config = ConfigDict(from_attributes=True)


class WeatherHistoryResponse(BaseModel):
    """Consolidated weather observations, rolling rainfall, and forecast window."""

    plot_id: int
    current_observation: Optional[WeatherObservationResponse] = None
    historical_observations: list[WeatherObservationResponse] = []
    forecast_window: list[WeatherForecastResponse] = []
    rolling_24h_rainfall_mm: float = 0.0
    rolling_72h_rainfall_mm: float = 0.0
    is_storm_hazard: bool = False


class SatelliteObservationResponse(BaseModel):
    """Sentinel-2 multispectral vegetation and moisture indices."""

    id: int
    plot_id: int
    acquisition_date: date
    stac_item_id: Optional[str] = None
    cloud_cover_percent: float
    mean_ndvi: float
    mean_ndwi: float
    mean_ndmi: Optional[float] = None
    min_ndvi: Optional[float] = None
    max_ndvi: Optional[float] = None
    std_ndvi: Optional[float] = None
    pixel_validity_count: int
    status: str  # MEASURED, CLOUD_OCCLUDED, SYNTHETIC_FALLBACK
    source: str
    provenance_type: str
    quality_score: float

    model_config = ConfigDict(from_attributes=True)


class SatelliteTimeSeriesResponse(BaseModel):
    """Vegetation trajectory and canopy vigor trend."""

    plot_id: int
    latest: Optional[SatelliteObservationResponse] = None
    timeseries: list[SatelliteObservationResponse] = []
    vegetation_status: str = "MODERATE_VIGOR"


class TerrainTopographyResponse(BaseModel):
    """Digital Elevation Model slope, TWI, and erosion hazard."""

    id: int
    plot_id: int
    elevation_m: float
    slope_percent: float
    slope_degrees: float
    twi: float
    erosion_hazard: str
    actionable_directive: Optional[str] = None
    source: str
    provenance_type: str
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnvironmentalSyncResponse(BaseModel):
    """Outcome summary of an on-demand multi-layer environmental synchronization."""

    plot_id: int
    status: str = "SUCCESS"
    weather_synced: bool = True
    satellite_synced: bool = True
    groundwater_synced: bool = True
    terrain_synced: bool = True
    hazard_state: str = "NORMAL_MODE"
    summary: str = "All environmental layers successfully refreshed."

