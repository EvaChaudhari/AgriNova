"""Multi-Source Weather Ingestion Adapter.

Ingests meteorological observations and 5-7 day rolling forecasts from OpenWeatherMap/IMD.
Calculates rolling 24h and 72h cumulative precipitation to feed the Hazard State Machine.
Provides deterministic agro-climatic fallbacks during network disruptions.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
import httpx

from app.core.config import settings
from app.services.fallback_data import IMD_AGROCLIMATIC_NORMALS
from app.services.weather_service import WeatherSnapshot, fetch_weather_data


@dataclass(frozen=True)
class DailyForecastSummary:
    """Aggregated daily forecast metrics."""

    forecast_date: date
    temp_min_c: float
    temp_max_c: float
    rainfall_mm: float
    precipitation_probability: float  # 0.0 - 100.0%
    condition_code: str
    condition_description: str


@dataclass(frozen=True)
class AggregatedWeatherBundle:
    """Comprehensive weather observation and multi-day forecast bundle."""

    observation: WeatherSnapshot
    forecasts: list[DailyForecastSummary]
    rolling_24h_rainfall_mm: float
    rolling_72h_rainfall_mm: float
    is_storm_hazard: bool
    source: str
    provenance_type: str
    quality_score: float


class WeatherIngestionService:
    """Multi-source weather ingestion with rolling precipitation aggregation."""

    STORM_24H_THRESHOLD_MM = 50.0
    STORM_72H_THRESHOLD_MM = 100.0

    @classmethod
    async def ingest_weather_bundle(
        cls,
        latitude: float,
        longitude: float,
        simulated_live_rain_mm: Optional[float] = None,
    ) -> AggregatedWeatherBundle:
        """Fetch current weather and rolling 5-day forecasts, computing cumulative rainfall."""
        # 1. Fetch current observation
        snapshot = await fetch_weather_data(latitude, longitude)
        if simulated_live_rain_mm is not None:
            # For testing/hazard overrides
            snapshot = WeatherSnapshot(
                t_min=snapshot.t_min,
                t_max=snapshot.t_max,
                t_mean=snapshot.t_mean,
                rh_mean=snapshot.rh_mean,
                wind_speed_2m=snapshot.wind_speed_2m,
                solar_radiation_mj_m2=snapshot.solar_radiation_mj_m2,
                rainfall_24h_mm=round(simulated_live_rain_mm, 1),
                seasonal_deficit_percent=snapshot.seasonal_deficit_percent,
                source=snapshot.source,
                condition_description=snapshot.condition_description,
                recorded_at=snapshot.recorded_at,
            )

        # 2. Ingest or synthesize 5-day forecast
        forecasts = await cls._fetch_or_synthesize_forecasts(latitude, longitude, snapshot)

        # 3. Calculate rolling cumulative rainfall
        rolling_24h = snapshot.rainfall_24h_mm
        next_48h_rain = sum(f.rainfall_mm for f in forecasts[:2])
        rolling_72h = round(rolling_24h + next_48h_rain, 1)

        # 4. Check hazard storm trigger
        is_storm = (
            rolling_24h >= cls.STORM_24H_THRESHOLD_MM
            or rolling_72h >= cls.STORM_72H_THRESHOLD_MM
            or any(f.rainfall_mm >= cls.STORM_24H_THRESHOLD_MM for f in forecasts[:2])
        )

        source = "OPENWEATHERMAP_LIVE" if snapshot.source == "LIVE_API" else "AGRO_CLIMATIC_FALLBACK"
        provenance = "MEASURED" if snapshot.source == "LIVE_API" else "SYNTHETIC_FALLBACK"
        quality = 1.0 if snapshot.source == "LIVE_API" else 0.85

        return AggregatedWeatherBundle(
            observation=snapshot,
            forecasts=forecasts,
            rolling_24h_rainfall_mm=round(rolling_24h, 1),
            rolling_72h_rainfall_mm=round(rolling_72h, 1),
            is_storm_hazard=is_storm,
            source=source,
            provenance_type=provenance,
            quality_score=quality,
        )

    @classmethod
    async def _fetch_or_synthesize_forecasts(
        cls,
        latitude: float,
        longitude: float,
        snapshot: WeatherSnapshot,
    ) -> list[DailyForecastSummary]:
        """Fetch live OpenWeatherMap 5-day forecast or generate deterministic fallback."""
        if settings.OPENWEATHERMAP_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=3.5) as client:
                    url = (
                        f"https://api.openweathermap.org/data/2.5/forecast"
                        f"?lat={latitude}&lon={longitude}&appid={settings.OPENWEATHERMAP_API_KEY}&units=metric"
                    )
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        return cls._parse_owm_forecast_json(data)
            except Exception:
                pass

        # Deterministic fallback based on month normals
        return cls._generate_fallback_forecasts(snapshot)

    @classmethod
    def _parse_owm_forecast_json(cls, data: dict[str, Any]) -> list[DailyForecastSummary]:
        """Aggregate 3-hourly OpenWeatherMap forecast points into daily summaries."""
        list_items = data.get("list", [])
        daily_bins: dict[str, list[dict[str, Any]]] = {}

        for item in list_items:
            dt_txt = item.get("dt_txt", "")
            if not dt_txt:
                continue
            day_str = dt_txt.split(" ")[0]
            if day_str not in daily_bins:
                daily_bins[day_str] = []
            daily_bins[day_str].append(item)

        forecasts: list[DailyForecastSummary] = []
        for day_str, items in list(daily_bins.items())[:5]:
            temps = [it.get("main", {}).get("temp", 25.0) for it in items]
            t_min = round(float(min(temps)), 1)
            t_max = round(float(max(temps)), 1)
            total_rain = round(sum(it.get("rain", {}).get("3h", 0.0) for it in items), 1)
            pop = round(max([it.get("pop", 0.0) for it in items]) * 100.0, 1)
            cond = items[0].get("weather", [{}])[0].get("main", "Clouds")
            desc = items[0].get("weather", [{}])[0].get("description", "overcast clouds").capitalize()

            forecasts.append(
                DailyForecastSummary(
                    forecast_date=date.fromisoformat(day_str),
                    temp_min_c=t_min,
                    temp_max_c=t_max,
                    rainfall_mm=total_rain,
                    precipitation_probability=pop,
                    condition_code=cond.upper(),
                    condition_description=desc,
                )
            )

        return forecasts

    @classmethod
    def _generate_fallback_forecasts(cls, snapshot: WeatherSnapshot) -> list[DailyForecastSummary]:
        """Generate deterministic 5-day daily forecast based on seasonal normals."""
        today = date.today()
        base_tmin = snapshot.t_min
        base_tmax = snapshot.t_max
        base_rain = snapshot.rainfall_24h_mm

        # Deterministic variations for 5 days
        offsets = [
            (0.0, 0.0, 1.0, 20.0, "CLEAR", "Clear skies with light sunshine"),
            (0.5, -0.5, 0.8, 25.0, "CLOUDS", "Scattered cumulus clouds"),
            (-0.5, 1.0, 0.5, 15.0, "CLEAR", "Sunny and dry conditions"),
            (1.0, -1.0, 1.2, 35.0, "RAIN", "Isolated afternoon showers"),
            (0.2, 0.3, 0.6, 20.0, "CLOUDS", "Partly cloudy"),
        ]

        forecasts = []
        for i, (tmin_off, tmax_off, rain_mult, pop, code, desc) in enumerate(offsets):
            f_date = today + timedelta(days=i + 1)
            day_rain = round(base_rain * rain_mult, 1)
            forecasts.append(
                DailyForecastSummary(
                    forecast_date=f_date,
                    temp_min_c=round(base_tmin + tmin_off, 1),
                    temp_max_c=round(base_tmax + tmax_off, 1),
                    rainfall_mm=day_rain,
                    precipitation_probability=pop,
                    condition_code=code,
                    condition_description=desc,
                )
            )
        return forecasts

