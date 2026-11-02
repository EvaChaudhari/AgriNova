"""Observation and Environmental Telemetry Repository.

Provides unified database operations for saving and querying weather time-series,
forecasts, satellite spectral curves, groundwater hydrographs, and terrain topography.
"""

from datetime import date, datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.engines.satellite_processor import SatelliteZonalResult
from app.engines.terrain_engine import TerrainAnalysisResult
from app.models.observations import (
    GroundwaterTimeSeries,
    SatelliteObservation,
    TerrainTopography,
    WeatherForecast,
    WeatherObservation,
)
from app.services.weather_ingestion import DailyForecastSummary
from app.services.weather_service import WeatherSnapshot
from app.services.wris_service import WRISStationRecord


class ObservationRepository:
    """Repository managing environmental observations and spatial telemetry."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -------------------------------------------------------------------------
    # Weather Observations & Forecasts
    # -------------------------------------------------------------------------
    def save_weather_observation(
        self,
        plot_id: int,
        snapshot: WeatherSnapshot,
        source: Optional[str] = None,
        provenance_type: Optional[str] = None,
        quality_score: Optional[float] = None,
    ) -> WeatherObservation:
        """Record instantaneous or 24h weather snapshot."""
        obs = WeatherObservation(
            plot_id=plot_id,
            observation_time=datetime.now(timezone.utc),
            temp_min_c=snapshot.t_min,
            temp_max_c=snapshot.t_max,
            temp_mean_c=snapshot.t_mean,
            relative_humidity_percent=snapshot.rh_mean,
            wind_speed_2m_mps=snapshot.wind_speed_2m,
            solar_radiation_mj_m2=snapshot.solar_radiation_mj_m2,
            rainfall_24h_mm=snapshot.rainfall_24h_mm,
            source=source or snapshot.source,
            provenance_type=provenance_type or ("MEASURED" if snapshot.source == "LIVE_API" else "SYNTHETIC_FALLBACK"),
            quality_score=quality_score if quality_score is not None else (1.0 if snapshot.source == "LIVE_API" else 0.85),
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def get_weather_history(self, plot_id: int, limit: int = 30) -> list[WeatherObservation]:
        """Fetch historical meteorological observations for a plot."""
        return (
            self.db.query(WeatherObservation)
            .filter(WeatherObservation.plot_id == plot_id)
            .order_by(WeatherObservation.observation_time.desc())
            .limit(limit)
            .all()
        )

    def save_weather_forecasts(
        self,
        plot_id: int,
        forecasts: list[DailyForecastSummary],
        source: str = "OPENWEATHERMAP_FORECAST",
        provenance_type: str = "FORECAST",
    ) -> list[WeatherForecast]:
        """Replace or append multi-day rolling forecast window."""
        # Clear previous forecast for plot to maintain clean window
        self.db.query(WeatherForecast).filter(WeatherForecast.plot_id == plot_id).delete()

        entities: list[WeatherForecast] = []
        now = datetime.now(timezone.utc)
        for f in forecasts:
            wf = WeatherForecast(
                plot_id=plot_id,
                forecast_issued_at=now,
                forecast_date=f.forecast_date,
                temp_min_c=f.temp_min_c,
                temp_max_c=f.temp_max_c,
                rainfall_mm=f.rainfall_mm,
                precipitation_probability=f.precipitation_probability,
                condition_code=f.condition_code,
                condition_description=f.condition_description,
                source=source,
                provenance_type=provenance_type,
            )
            self.db.add(wf)
            entities.append(wf)

        self.db.commit()
        for e in entities:
            self.db.refresh(e)
        return entities

    def get_latest_forecasts(self, plot_id: int) -> list[WeatherForecast]:
        """Fetch active rolling forecast window for a plot."""
        return (
            self.db.query(WeatherForecast)
            .filter(WeatherForecast.plot_id == plot_id)
            .order_by(WeatherForecast.forecast_date.asc())
            .all()
        )

    # -------------------------------------------------------------------------
    # Satellite Observations
    # -------------------------------------------------------------------------
    def save_satellite_observation(
        self,
        plot_id: int,
        result: SatelliteZonalResult,
    ) -> SatelliteObservation:
        """Store Sentinel-2 zonal statistics or synthetic phenological calculation."""
        obs = SatelliteObservation(
            plot_id=plot_id,
            acquisition_date=result.acquisition_date,
            stac_item_id=result.stac_item_id,
            cloud_cover_percent=result.cloud_cover_percent,
            mean_ndvi=result.mean_ndvi,
            mean_ndwi=result.mean_ndwi,
            mean_ndmi=result.mean_ndmi,
            min_ndvi=result.min_ndvi,
            max_ndvi=result.max_ndvi,
            std_ndvi=result.std_ndvi,
            pixel_validity_count=result.pixel_validity_count,
            status=result.status,
            source=result.source,
            provenance_type=result.provenance_type,
            quality_score=result.quality_score,
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def get_satellite_timeseries(self, plot_id: int, limit: int = 20) -> list[SatelliteObservation]:
        """Fetch vegetation index trajectory for a field."""
        return (
            self.db.query(SatelliteObservation)
            .filter(SatelliteObservation.plot_id == plot_id)
            .order_by(SatelliteObservation.acquisition_date.desc())
            .limit(limit)
            .all()
        )

    # -------------------------------------------------------------------------
    # Groundwater Hydrograph Time-Series
    # -------------------------------------------------------------------------
    def save_groundwater_record(
        self,
        plot_id: int,
        record: WRISStationRecord,
    ) -> GroundwaterTimeSeries:
        """Persist latest hydrograph station record for plot."""
        gw = GroundwaterTimeSeries(
            plot_id=plot_id,
            station_id=record.station_id,
            station_name=record.station_name,
            record_date=date.today(),
            depth_mbgl=record.current_depth_mbgl,
            season_flag="PRE_MONSOON" if date.today().month in [4, 5, 6] else "POST_MONSOON",
            five_year_decline_rate_m_yr=record.five_year_decline_rate_m_yr,
            distance_km=record.distance_km,
            source=record.source,
            provenance_type=record.provenance_type,
            quality_score=record.quality_score,
        )
        self.db.add(gw)
        self.db.commit()
        self.db.refresh(gw)
        return gw

    def get_latest_groundwater_record(self, plot_id: int) -> Optional[GroundwaterTimeSeries]:
        """Retrieve most recent water table depth record."""
        return (
            self.db.query(GroundwaterTimeSeries)
            .filter(GroundwaterTimeSeries.plot_id == plot_id)
            .order_by(GroundwaterTimeSeries.record_date.desc())
            .first()
        )

    # -------------------------------------------------------------------------
    # Terrain Topography
    # -------------------------------------------------------------------------
    def save_or_update_terrain(
        self,
        plot_id: int,
        result: TerrainAnalysisResult,
    ) -> TerrainTopography:
        """Upsert terrain and DEM analysis record for a plot."""
        existing = (
            self.db.query(TerrainTopography)
            .filter(TerrainTopography.plot_id == plot_id)
            .first()
        )
        if not existing:
            terrain = TerrainTopography(
                plot_id=plot_id,
                elevation_m=result.elevation_m,
                slope_percent=result.slope_percent,
                slope_degrees=result.slope_degrees,
                twi=result.twi,
                erosion_hazard=result.erosion_hazard,
                actionable_directive=result.actionable_directive,
                source=result.source,
                provenance_type=result.provenance_type,
                quality_score=result.quality_score,
                calculated_at=datetime.now(timezone.utc),
            )
            self.db.add(terrain)
        else:
            existing.elevation_m = result.elevation_m
            existing.slope_percent = result.slope_percent
            existing.slope_degrees = result.slope_degrees
            existing.twi = result.twi
            existing.erosion_hazard = result.erosion_hazard
            existing.actionable_directive = result.actionable_directive
            existing.source = result.source
            existing.provenance_type = result.provenance_type
            existing.quality_score = result.quality_score
            existing.calculated_at = datetime.now(timezone.utc)
            terrain = existing

        self.db.commit()
        self.db.refresh(terrain)
        return terrain

    def get_terrain_topography(self, plot_id: int) -> Optional[TerrainTopography]:
        """Fetch terrain and slope classification for a plot."""
        return (
            self.db.query(TerrainTopography)
            .filter(TerrainTopography.plot_id == plot_id)
            .first()
        )

