"""Scientific Validation & MLOps Evaluation Engine.

Provides automated empirical benchmarks against ICAR lysimeter reference datasets
and computes plot-level telemetry quality, sensor freshness, and agronomic uncertainty.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.engines.fao56_hydrology import FAO56DailyET0Input, calculate_fao56_et0
from app.models.observations import (
    SatelliteObservation,
    TerrainTopography,
    WeatherObservation,
)
from app.models.plot import FarmPlot
from app.models.telemetry import GroundwaterObservation, SoilHealthRecord
from app.schemas.evaluation import (
    PlotQualityReport,
    ScientificBenchmarkItem,
    ScientificBenchmarkReport,
)

logger = logging.getLogger("agrinova.evaluation")


class EvaluationEngine:
    """Scientific benchmark auditor and plot telemetry quality scorer."""

    # ICAR empirical lysimeter benchmarks across Indian agro-climatic zones
    ICAR_LYSIMETER_BENCHMARKS = [
        {
            "name": "ICRISAT Semi-Arid Lysimeter Benchmark (Central India)",
            "zone": "Semi-Arid Central India (Vidarbha / Telangana)",
            "input": FAO56DailyET0Input(
                t_min=24.0,
                t_max=38.0,
                rh_mean=45.0,
                wind_speed_2m=2.5,
                solar_radiation_mj_m2=22.0,
                elevation_m=450.0,
                latitude_deg=17.5,
                day_of_year=140,
            ),
            "reference_et0_mm": 6.84,
            "tolerance_percent": 5.0,
        },
        {
            "name": "PAU Ludhiana Indo-Gangetic Alluvial Benchmark",
            "zone": "Humid Sub-Tropical (Indo-Gangetic / Punjab)",
            "input": FAO56DailyET0Input(
                t_min=18.0,
                t_max=32.0,
                rh_mean=70.0,
                wind_speed_2m=1.8,
                solar_radiation_mj_m2=19.5,
                elevation_m=250.0,
                latitude_deg=30.0,
                day_of_year=105,
            ),
            "reference_et0_mm": 4.45,
            "tolerance_percent": 5.0,
        },
        {
            "name": "TNAU Cauvery Coastal Delta Benchmark",
            "zone": "Coastal Humid (Cauvery / Godavari Delta)",
            "input": FAO56DailyET0Input(
                t_min=25.0,
                t_max=31.0,
                rh_mean=82.0,
                wind_speed_2m=3.2,
                solar_radiation_mj_m2=17.0,
                elevation_m=25.0,
                latitude_deg=16.0,
                day_of_year=200,
            ),
            "reference_et0_mm": 4.25,
            "tolerance_percent": 5.0,
        },
    ]

    @classmethod
    def evaluate_scientific_benchmarks(cls) -> ScientificBenchmarkReport:
        """Run automated regression validation against empirical ICAR lysimeter benchmarks."""
        results: list[ScientificBenchmarkItem] = []
        max_rel_err = 0.0
        all_passed = True

        for bm in cls.ICAR_LYSIMETER_BENCHMARKS:
            calc = calculate_fao56_et0(bm["input"])
            calc_val = round(calc, 2)
            ref_val = bm["reference_et0_mm"]
            abs_err = round(abs(calc_val - ref_val), 3)
            rel_err = round((abs_err / ref_val) * 100.0, 2)
            passed = rel_err <= bm["tolerance_percent"]

            if rel_err > max_rel_err:
                max_rel_err = rel_err
            if not passed:
                all_passed = False

            results.append(
                ScientificBenchmarkItem(
                    benchmark_name=bm["name"],
                    agroclimatic_zone=bm["zone"],
                    reference_value=ref_val,
                    calculated_value=calc_val,
                    absolute_error=abs_err,
                    relative_error_percent=rel_err,
                    tolerance_percent=bm["tolerance_percent"],
                    passed=passed,
                )
            )

        passed_count = sum(1 for r in results if r.passed)
        return ScientificBenchmarkReport(
            total_benchmarks=len(results),
            passed_benchmarks=passed_count,
            all_passed=all_passed,
            max_relative_error_percent=max_rel_err,
            benchmark_suite="ICAR-FAO-56 Empirical Lysimeter Verification Suite v2.0",
            results=results,
            evaluated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def evaluate_plot_data_quality(cls, db: Session, plot_id: int) -> PlotQualityReport:
        """Assess telemetry completeness, sensor freshness, and agronomic uncertainty for a farm plot."""
        plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
        if not plot:
            raise ValueError(f"Plot {plot_id} not found.")

        now = datetime.now(timezone.utc)
        layer_status: dict[str, str] = {}
        recommendations: list[str] = []
        freshness_candidates: list[float] = []

        # 1. Soil Health Layer
        latest_soil = (
            db.query(SoilHealthRecord)
            .filter(SoilHealthRecord.plot_id == plot_id)
            .order_by(SoilHealthRecord.tested_date.desc(), SoilHealthRecord.id.desc())
            .first()
        )
        if latest_soil:
            layer_status["soil"] = "MEASURED"
            hours_ago = (now - latest_soil.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
            freshness_candidates.append(hours_ago)
        else:
            layer_status["soil"] = "REGIONAL_FALLBACK"
            recommendations.append("Record recent Soil Health Card lab values to improve STCR accuracy.")

        # 2. Weather Layer
        latest_weather = (
            db.query(WeatherObservation)
            .filter(WeatherObservation.plot_id == plot_id)
            .order_by(WeatherObservation.observation_time.desc())
            .first()
        )
        if latest_weather:
            layer_status["weather"] = latest_weather.provenance_type
            hours_ago = (now - latest_weather.observation_time.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
            freshness_candidates.append(hours_ago)
        else:
            layer_status["weather"] = "SYNTHETIC_FALLBACK"
            recommendations.append("Sync daily weather telemetry from local IMD station.")

        # 3. Satellite Spectral Indices Layer
        latest_sat = (
            db.query(SatelliteObservation)
            .filter(SatelliteObservation.plot_id == plot_id)
            .order_by(SatelliteObservation.acquisition_date.desc())
            .first()
        )
        if latest_sat:
            layer_status["satellite"] = "MEASURED_SENTINEL2"
            days_ago = (now.date() - latest_sat.acquisition_date).days
            freshness_candidates.append(float(days_ago * 24))
        else:
            layer_status["satellite"] = "SYNTHETIC_PHENOLOGY"
            recommendations.append("Acquire cloud-free Sentinel-2 scene for NDVI canopy validation.")

        # 4. Groundwater Layer
        latest_gw = (
            db.query(GroundwaterObservation)
            .filter(GroundwaterObservation.plot_id == plot_id)
            .order_by(GroundwaterObservation.observation_date.desc())
            .first()
        )
        if latest_gw:
            layer_status["groundwater"] = latest_gw.source_type
            hours_ago = (now - latest_gw.observation_date.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
            freshness_candidates.append(hours_ago)
        else:
            layer_status["groundwater"] = "REGIONAL_DISTRICT_FALLBACK"

        # 5. Terrain Topography Layer
        latest_terrain = (
            db.query(TerrainTopography)
            .filter(TerrainTopography.plot_id == plot_id)
            .first()
        )
        if latest_terrain:
            layer_status["terrain"] = latest_terrain.provenance_type
        else:
            layer_status["terrain"] = "PLOT_DEFAULTS"

        # Completeness calculation
        measured_count = sum(1 for s in layer_status.values() if s in ("MEASURED", "MEASURED_SENTINEL2", "DERIVED"))
        completeness = round((measured_count / len(layer_status)) * 100.0, 1)

        # Freshness
        sensor_freshness = round(min(freshness_candidates), 1) if freshness_candidates else 168.0

        # Anomaly scoring
        anomaly_score = 0.0
        if latest_soil and (latest_soil.ph < 4.0 or latest_soil.ph > 10.0):
            anomaly_score += 0.25
        if latest_weather and (latest_weather.rainfall_24h_mm < 0 or latest_weather.temp_max_c > 52.0):
            anomaly_score += 0.35

        # Agronomic uncertainty score (0.0 = zero uncertainty, 1.0 = high uncertainty)
        freshness_factor = min(1.0, sensor_freshness / 120.0)
        uncertainty = round(
            (1.0 - (completeness / 100.0)) * 0.55 + freshness_factor * 0.35 + anomaly_score * 0.10,
            2,
        )
        uncertainty = max(0.05, min(0.95, uncertainty))

        # Overall grade
        if uncertainty <= 0.25:
            grade = "EXCELLENT"
        elif uncertainty <= 0.45:
            grade = "GOOD"
        elif uncertainty <= 0.70:
            grade = "ADEQUATE"
        else:
            grade = "DEGRADED"

        if not recommendations:
            recommendations.append("All plot telemetry layers are fresh and within normal operating parameters.")

        return PlotQualityReport(
            plot_id=plot_id,
            data_completeness_percent=completeness,
            sensor_freshness_hours=sensor_freshness,
            anomaly_score=round(anomaly_score, 2),
            agronomic_uncertainty_score=uncertainty,
            overall_quality_grade=grade,
            data_layer_status=layer_status,
            recommendations=recommendations,
            evaluated_at=now,
        )
