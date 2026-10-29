"""Telemetry and physical sensor models.

Stores groundwater monitoring depth and Soil Health Card NPK/pH records.
"""

from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class GroundwaterObservation(Base):
    __tablename__ = "groundwater_observations"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=True, index=True)
    depth_mbgl = Column(Float, nullable=False)  # Meters Below Ground Level
    source_type = Column(String(32), nullable=False, default="FALLBACK_DISTRICT")  # HARDWARE_SENSOR, INDIA_WRIS, FALLBACK_DISTRICT
    observation_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    plot = relationship("FarmPlot", back_populates="groundwater_observations")


class SoilHealthRecord(Base):
    __tablename__ = "soil_health_records"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="CASCADE"), nullable=False, index=True)
    nitrogen_kg_ha = Column(Float, nullable=False)
    phosphorus_kg_ha = Column(Float, nullable=False)
    potassium_kg_ha = Column(Float, nullable=False)
    ph = Column(Float, nullable=False)
    organic_carbon_percent = Column(Float, nullable=False)
    source_type = Column(String(32), nullable=False, default="REGIONAL_FALLBACK")  # SOIL_HEALTH_CARD_API, LAB_TEST, REGIONAL_FALLBACK
    tested_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    plot = relationship("FarmPlot", back_populates="soil_health_records")

