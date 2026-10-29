"""Weather Service Adapter.

Integrates IMD / OpenWeatherMap APIs with deterministic regional agro-climatic fallback.
Ensures zero runtime failure during network disruption.
"""

from datetime import datetime, timezone
from dataclasses import dataclass
import httpx

from app.core.config import settings
from app.services.fallback_data import IMD_AGROCLIMATIC_NORMALS


@dataclass(frozen=True)
class WeatherSnapshot:
    """Standardized meteorological observations and 24h forecasts."""
    t_min: float
    t_max: float
    t_mean: float
    rh_mean: float
    wind_speed_2m: float
    solar_radiation_mj_m2: float
    rainfall_24h_mm: float
    seasonal_deficit_percent: float
    source: str  # LIVE_API or AGRO_CLIMATIC_FALLBACK
    condition_description: str
    recorded_at: str


async def fetch_weather_data(latitude: float, longitude: float) -> WeatherSnapshot:
    """Fetch live weather from OpenWeatherMap or fallback to IMD agro-climatic normal."""
    now = datetime.now(timezone.utc)
    current_month = now.month

    # 1. Attempt live API if key is provided
    if settings.OPENWEATHERMAP_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                url = (
                    f"https://api.openweathermap.org/data/2.5/weather"
                    f"?lat={latitude}&lon={longitude}&appid={settings.OPENWEATHERMAP_API_KEY}&units=metric"
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    main = data.get("main", {})
                    wind = data.get("wind", {})
                    rain = data.get("rain", {})
                    weather_desc = data.get("weather", [{}])[0].get("description", "Clear sky")

                    t_min = float(main.get("temp_min", 22.0))
                    t_max = float(main.get("temp_max", 34.0))
                    t_mean = float(main.get("temp", (t_min + t_max) / 2.0))
                    rh = float(main.get("humidity", 60.0))
                    wind_speed = float(wind.get("speed", 2.0))
                    rain_1h = float(rain.get("1h", 0.0))
                    rain_24h = rain_1h * 24.0 if rain_1h > 0 else 0.0

                    normal = IMD_AGROCLIMATIC_NORMALS.get(current_month, IMD_AGROCLIMATIC_NORMALS[7])

                    return WeatherSnapshot(
                        t_min=round(t_min, 1),
                        t_max=round(t_max, 1),
                        t_mean=round(t_mean, 1),
                        rh_mean=round(rh, 1),
                        wind_speed_2m=round(wind_speed, 1),
                        solar_radiation_mj_m2=normal["radiation"],
                        rainfall_24h_mm=round(rain_24h, 1),
                        seasonal_deficit_percent=normal["deficit_pct"],
                        source="LIVE_API",
                        condition_description=weather_desc.capitalize(),
                        recorded_at=now.isoformat(),
                    )
        except Exception:
            # Fall through gracefully to deterministic agro-climatic normals
            pass

    # 2. Deterministic Agro-climatic Fallback
    normal = IMD_AGROCLIMATIC_NORMALS.get(current_month, IMD_AGROCLIMATIC_NORMALS[7])
    t_min = normal["t_min"]
    t_max = normal["t_max"]
    t_mean = round((t_min + t_max) / 2.0, 1)

    return WeatherSnapshot(
        t_min=t_min,
        t_max=t_max,
        t_mean=t_mean,
        rh_mean=normal["rh"],
        wind_speed_2m=normal["wind_speed"],
        solar_radiation_mj_m2=normal["radiation"],
        rainfall_24h_mm=normal["rain_24h"],
        seasonal_deficit_percent=normal["deficit_pct"],
        source="AGRO_CLIMATIC_FALLBACK",
        condition_description="Seasonal agro-climatic baseline normal",
        recorded_at=now.isoformat(),
    )

