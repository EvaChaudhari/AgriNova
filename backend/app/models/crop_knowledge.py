"""Crop Knowledge Base & Agronomic Intelligence Models.

Implements database-backed, versioned agronomic repositories for crops,
varieties, FAO-56 phenological growth stages, ICAR STCR nutrient benchmarks,
and CIB&RC-approved IPM pest profiles.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Crop(Base):
    """Primary agronomic crop taxonomy and seasonal classification."""

    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(80), unique=True, nullable=False, index=True)
    scientific_name = Column(String(120), nullable=False)
    season = Column(String(32), nullable=False)  # KHARIF, RABI, ZAID
    category = Column(String(32), nullable=False)  # CEREAL, PULSE, OILSEED, FIBRE, CASH
    standard_duration_days = Column(Integer, nullable=False, default=120)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    varieties = relationship("CropVariety", back_populates="crop", cascade="all, delete-orphan")
    growth_stages = relationship(
        "CropGrowthStage",
        back_populates="crop",
        cascade="all, delete-orphan",
        order_by="CropGrowthStage.start_das",
    )
    nutrient_benchmark = relationship(
        "CropNutrientBenchmark",
        back_populates="crop",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pest_profiles = relationship(
        "CropPestProfile",
        back_populates="crop",
        cascade="all, delete-orphan",
    )


class CropVariety(Base):
    """Cultivar and hybrid agronomic characteristics with stress tolerance."""

    __tablename__ = "crop_varieties"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    variety_name = Column(String(120), nullable=False)
    duration_days = Column(Integer, nullable=False)
    drought_tolerance = Column(String(32), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    flood_tolerance = Column(String(32), nullable=False, default="LOW")  # HIGH, MEDIUM, LOW
    potential_yield_q_ha = Column(Float, nullable=False, default=25.0)  # Quintals per hectare

    # Relationships
    crop = relationship("Crop", back_populates="varieties")


class CropGrowthStage(Base):
    """FAO-56 phenological stage parameters, rooting depths, and water stress factors."""

    __tablename__ = "crop_growth_stages"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(32), nullable=False)  # INITIAL, VEGETATIVE, FLOWERING, MATURITY
    start_das = Column(Integer, nullable=False)  # Days After Sowing
    end_das = Column(Integer, nullable=False)
    kc = Column(Float, nullable=False)  # FAO-56 crop coefficient
    rooting_depth_m = Column(Float, nullable=False)  # Zr in meters
    depletion_fraction_p = Column(Float, nullable=False, default=0.50)  # Allowable depletion fraction
    ky = Column(Float, nullable=False, default=1.0)  # Water stress yield response factor
    critical_water_stage = Column(Boolean, nullable=False, default=False)

    # Relationships
    crop = relationship("Crop", back_populates="growth_stages")


class CropNutrientBenchmark(Base):
    """ICAR Soil Test Crop Response (STCR) targeted yield equations and safe thresholds."""

    __tablename__ = "crop_nutrient_benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # STCR Coefficients: Fertilizer = A * TargetYield - B * SoilTestValue
    stcr_a_n = Column(Float, nullable=False)
    stcr_b_n = Column(Float, nullable=False)
    stcr_a_p = Column(Float, nullable=False)
    stcr_b_p = Column(Float, nullable=False)
    stcr_a_k = Column(Float, nullable=False)
    stcr_b_k = Column(Float, nullable=False)
    
    # Safe Upper Bounds (ICAR Maximum Recommended Doses in kg/ha)
    max_n_kg_ha = Column(Float, nullable=False, default=200.0)
    max_p_kg_ha = Column(Float, nullable=False, default=100.0)
    max_k_kg_ha = Column(Float, nullable=False, default=100.0)
    target_yield_default_q_ha = Column(Float, nullable=False, default=25.0)

    # Relationships
    crop = relationship("Crop", back_populates="nutrient_benchmark")


class CropPestProfile(Base):
    """CIB&RC-compliant Integrated Pest Management (IPM) guidelines and symptoms."""

    __tablename__ = "crop_pest_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True)
    pest_name = Column(String(120), nullable=False)
    pest_type = Column(String(32), nullable=False)  # INSECT, FUNGUS, BACTERIA, VIRUS, WEED
    affected_growth_stage = Column(String(32), nullable=False)  # INITIAL, VEGETATIVE, FLOWERING, MATURITY, ALL
    symptoms = Column(Text, nullable=False)
    economic_threshold_etl = Column(String(120), nullable=False)
    ipm_practice = Column(Text, nullable=False)
    approved_chemical = Column(String(120), nullable=True)
    cib_restriction = Column(String(255), nullable=True)

    # Relationships
    crop = relationship("Crop", back_populates="pest_profiles")

