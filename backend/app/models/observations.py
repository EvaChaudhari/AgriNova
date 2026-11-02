"""Persistent Environmental & Geospatial Observation Models.

Implements time-series storage for weather observations, rolling forecasts,
Sentinel-2 optical indices, groundwater hydrographs, and terrain topography.
Adheres to M01 ProvenanceMetadata and StandardObservationEnvelope standards.
"""

from datetime import datetime, timezone, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class WeatherObservation(Base):
    """Historical in-situ sensor or reanalysis meteorological time-series."""

    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    observation_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    temp_min_c = Column(Float, nullable=False)
    temp_max_c = Column(Float, nullable=False)
    temp_mean_c = Column(Float, nullable=False)
    relative_humidity_percent = Column(Float, nullable=False)
    wind_speed_2m_mps = Column(Float, nullable=False, default=2.0)
    solar_radiation_mj_m2 = Column(Float, nullable=False, default=18.0)
    rainfall_24h_mm = Column(Float, nullable=False, default=0.0)
    
    # Provenance and scientific quality lineage
    source = Column(String(64), nullable=False, default="OPENWEATHERMAP")  # OPENWEATHERMAP, IMD, HARDWARE_STATION, SYNTHETIC_FALLBACK
    provenance_type = Column(String(32), nullable=False, default="MEASURED")  # MEASURED, FORECAST, DERIVED, SYNTHETIC_FALLBACK
    quality_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    plot = relationship("FarmPlot", back_populates="weather_observations")


class WeatherForecast(Base):
    """Multi-day rolling meteorological forecast window with precipitation probabilities."""

    __tablename__ = "weather_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    forecast_date = Column(Date, nullable=False, index=True)
    temp_min_c = Column(Float, nullable=False)
    temp_max_c = Column(Float, nullable=False)
    rainfall_mm = Column(Float, nullable=False, default=0.0)
    precipitation_probability = Column(Float, nullable=False, default=0.0)  # 0.0 - 100.0%
    condition_code = Column(String(32), nullable=False, default="CLEAR")
    condition_description = Column(String(120), nullable=False, default="Clear Sky")

    # Provenance
    source = Column(String(64), nullable=False, default="OPENWEATHERMAP_FORECAST")
    provenance_type = Column(String(32), nullable=False, default="FORECAST")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    plot = relationship("FarmPlot", back_populates="weather_forecasts")


class SatelliteObservation(Base):
    """Sentinel-2 L2A optical spectral indices, cloud scores, and zonal statistics."""

    __tablename__ = "satellite_observations"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    acquisition_date = Column(Date, nullable=False, index=True)
    stac_item_id = Column(String(128), nullable=True)
    cloud_cover_percent = Column(Float, nullable=False, default=0.0)
    
    # Vegetation & Water Spectral Indices
    mean_ndvi = Column(Float, nullable=False)  # Normalized Difference Vegetation Index [-1, 1]
    mean_ndwi = Column(Float, nullable=False)  # Normalized Difference Water Index [-1, 1]
    mean_ndmi = Column(Float, nullable=True)  # Normalized Difference Moisture Index [-1, 1]
    min_ndvi = Column(Float, nullable=True)
    max_ndvi = Column(Float, nullable=True)
    std_ndvi = Column(Float, nullable=True)
    pixel_validity_count = Column(Integer, nullable=False, default=1)
    
    # Processing status and fallback indicators
    status = Column(String(32), nullable=False, default="MEASURED")  # MEASURED, CLOUD_OCCLUDED, SYNTHETIC_FALLBACK
    source = Column(String(64), nullable=False, default="SENTINEL_2_L2A")
    provenance_type = Column(String(32), nullable=False, default="DERIVED")
    quality_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    plot = relationship("FarmPlot", back_populates="satellite_observations")


class GroundwaterTimeSeries(Base):
    """Historical and seasonal hydrograph depth-to-water records from CGWB / India-WRIS."""

    __tablename__ = "groundwater_time_series"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    station_id = Column(String(64), nullable=True, index=True)
    station_name = Column(String(120), nullable=True)
    record_date = Column(Date, nullable=False, index=True)
    depth_mbgl = Column(Float, nullable=False)  # Depth to water level in meters below ground level
    season_flag = Column(String(32), nullable=False, default="MONSOON")  # PRE_MONSOON, POST_MONSOON, RABI, KHARIF
    five_year_decline_rate_m_yr = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)

    # Provenance
    source = Column(String(64), nullable=False, default="INDIA_WRIS")  # INDIA_WRIS, CGWB, SENSOR, FALLBACK_DISTRICT
    provenance_type = Column(String(32), nullable=False, default="MEASURED")
    quality_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    plot = relationship("FarmPlot", back_populates="groundwater_records")


class TerrainTopography(Base):
    """Digital Elevation Model (DEM) topographic, slope, wetness and erosion analysis."""

    __tablename__ = "terrain_topography"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    elevation_m = Column(Float, nullable=False, default=250.0)
    slope_percent = Column(Float, nullable=False, default=1.5)
    slope_degrees = Column(Float, nullable=False, default=0.86)
    aspect_degrees = Column(Float, nullable=True)
    twi = Column(Float, nullable=False, default=6.5)  # Topographic Wetness Index ln(a / tan(beta))
    erosion_hazard = Column(String(64), nullable=False, default="STABLE")  # HIGH_EROSION_RISK, WATERLOGGING_SUSCEPTIBLE, STABLE
    actionable_directive = Column(String(255), nullable=True)

    # Provenance
    source = Column(String(64), nullable=False, default="SRTM_DEM")  # SRTM_DEM, COPERNICUS_DEM, HYPSOMETRIC_FALLBACK
    provenance_type = Column(String(32), nullable=False, default="DERIVED")
    quality_score = Column(Float, nullable=False, default=1.0)
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    plot = relationship("FarmPlot", back_populates="terrain")

