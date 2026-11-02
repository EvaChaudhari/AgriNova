"""Soil Health Card (SHC) Ingestion & Nutrient Classification Service.

Parses laboratory or API Soil Health Card records, applies ICAR fertility ratings,
and associates soil test values with target farm plots.
"""

from datetime import date, datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.engines.fertilizer_engine import FertilizerEngine, NutrientRating
from app.models.plot import FarmPlot
from app.models.telemetry import SoilHealthRecord
from app.services.fallback_data import get_soil_benchmark


class SoilIngestionService:
    """Service ingesting and evaluating Soil Health Card physicochemical data."""

    @classmethod
    def ingest_soil_record(
        cls,
        db: Session,
        plot_id: int,
        nitrogen_kg_ha: Optional[float] = None,
        phosphorus_kg_ha: Optional[float] = None,
        potassium_kg_ha: Optional[float] = None,
        ph: Optional[float] = None,
        organic_carbon_percent: Optional[float] = None,
        source_type: str = "SOIL_HEALTH_CARD_API",
        tested_date: Optional[date] = None,
    ) -> tuple[SoilHealthRecord, NutrientRating]:
        """Ingest or update Soil Health Card measurements for a farm plot."""
        plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
        fallback_soil = get_soil_benchmark(plot.soil_texture if plot else "Vertisol")

        # Fall back to regional baseline if specific parameter is None
        n_val = float(nitrogen_kg_ha) if nitrogen_kg_ha is not None and nitrogen_kg_ha > 0 else fallback_soil["nitrogen_kg_ha"]
        p_val = float(phosphorus_kg_ha) if phosphorus_kg_ha is not None and phosphorus_kg_ha > 0 else fallback_soil["phosphorus_kg_ha"]
        k_val = float(potassium_kg_ha) if potassium_kg_ha is not None and potassium_kg_ha > 0 else fallback_soil["potassium_kg_ha"]
        ph_val = float(ph) if ph is not None and ph > 0 else fallback_soil["ph"]
        oc_val = float(organic_carbon_percent) if organic_carbon_percent is not None and organic_carbon_percent > 0 else fallback_soil["organic_carbon_percent"]

        record = SoilHealthRecord(
            plot_id=plot_id,
            nitrogen_kg_ha=round(n_val, 1),
            phosphorus_kg_ha=round(p_val, 1),
            potassium_kg_ha=round(k_val, 1),
            ph=round(ph_val, 2),
            organic_carbon_percent=round(oc_val, 2),
            source_type=source_type,
            tested_date=tested_date or date.today(),
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        # Compute qualitative fertility classification
        rating = FertilizerEngine.classify_soil_health(
            nitrogen_kg_ha=record.nitrogen_kg_ha,
            phosphorus_kg_ha=record.phosphorus_kg_ha,
            potassium_kg_ha=record.potassium_kg_ha,
            ph=record.ph,
            organic_carbon_percent=record.organic_carbon_percent,
        )

        return record, rating

    @classmethod
    def get_latest_soil_rating(cls, db: Session, plot_id: int) -> tuple[SoilHealthRecord, NutrientRating]:
        """Fetch latest soil health record for plot or generate benchmark evaluation."""
        record = (
            db.query(SoilHealthRecord)
            .filter(SoilHealthRecord.plot_id == plot_id)
            .order_by(SoilHealthRecord.tested_date.desc(), SoilHealthRecord.id.desc())
            .first()
        )
        if not record:
            record, rating = cls.ingest_soil_record(db, plot_id, source_type="REGIONAL_FALLBACK")
            return record, rating

        rating = FertilizerEngine.classify_soil_health(
            nitrogen_kg_ha=record.nitrogen_kg_ha,
            phosphorus_kg_ha=record.phosphorus_kg_ha,
            potassium_kg_ha=record.potassium_kg_ha,
            ph=record.ph,
            organic_carbon_percent=record.organic_carbon_percent,
        )
        return record, rating

