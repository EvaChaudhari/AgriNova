"""Farm, Farm Plot and Crop Cycle models.

Stores geospatial field boundaries, agronomic metadata, and seasonal cropping cycles.
Supports parent Farm holding aggregating multiple plots.
"""

from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base, PostGISGeometry


class Farm(Base):
    """Parent Agricultural Holding aggregating multiple contiguous or disjoint farm plots."""

    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id = Column(String(128), ForeignKey("device_profiles.device_id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    village = Column(String(120), nullable=True)
    subdistrict = Column(String(120), nullable=True)
    district = Column(String(120), nullable=True)
    state = Column(String(120), nullable=True)
    total_area_hectares = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="farms")
    plots = relationship("FarmPlot", back_populates="farm", cascade="all, delete-orphan")


class FarmPlot(Base):
    __tablename__ = "farm_plots"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(String(128), ForeignKey("device_profiles.device_id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    survey_number = Column(String(64), nullable=True)
    khasra_number = Column(String(64), nullable=True)
    boundary = Column(PostGISGeometry("POLYGON", 4326), nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    area_hectares = Column(Float, nullable=False)
    soil_texture = Column(String(64), nullable=False, default="Vertisol")
    elevation_m = Column(Float, nullable=False, default=250.0)
    slope_percent = Column(Float, nullable=False, default=1.5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farm = relationship("Farm", back_populates="plots")
    device = relationship("DeviceProfile", back_populates="plots")
    crop_cycles = relationship("CropCycle", back_populates="plot", cascade="all, delete-orphan")
    groundwater_observations = relationship("GroundwaterObservation", back_populates="plot", cascade="all, delete-orphan")
    soil_health_records = relationship("SoilHealthRecord", back_populates="plot", cascade="all, delete-orphan")
    weather_observations = relationship("WeatherObservation", back_populates="plot", cascade="all, delete-orphan")
    weather_forecasts = relationship("WeatherForecast", back_populates="plot", cascade="all, delete-orphan")
    satellite_observations = relationship("SatelliteObservation", back_populates="plot", cascade="all, delete-orphan")
    groundwater_records = relationship("GroundwaterTimeSeries", back_populates="plot", cascade="all, delete-orphan")
    terrain = relationship("TerrainTopography", back_populates="plot", uselist=False, cascade="all, delete-orphan")


class CropCycle(Base):
    __tablename__ = "crop_cycles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    crop_name = Column(String(80), nullable=False)
    variety = Column(String(80), nullable=True)
    sowing_date = Column(Date, nullable=False, default=date.today)
    growth_stage = Column(String(32), nullable=False, default="INITIAL")  # INITIAL, VEGETATIVE, FLOWERING, MATURITY, HARVEST
    irrigation_method = Column(String(32), nullable=False, default="DRIP")  # DRIP, SPRINKLER, FLOOD, RAINFED
    is_active = Column(Boolean, nullable=False, default=True)
    expected_harvest_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    plot = relationship("FarmPlot", back_populates="crop_cycles")
