"""Unit Tests for Multi-Source Weather Ingestion Adapter (Milestone C)."""

from datetime import date
import pytest

from app.services.weather_ingestion import (
    AggregatedWeatherBundle,
    DailyForecastSummary,
    WeatherIngestionService,
)


@pytest.mark.asyncio
async def test_weather_bundle_ingestion_normal_conditions():
    """Verify normal weather bundle ingestion, 5-day daily forecast, and rolling rainfall."""
    bundle = await WeatherIngestionService.ingest_weather_bundle(
        latitude=17.50,
        longitude=78.50,
        simulated_live_rain_mm=5.0,
    )

    assert isinstance(bundle, AggregatedWeatherBundle)
    assert len(bundle.forecasts) == 5
    assert bundle.rolling_24h_rainfall_mm == 5.0
    assert bundle.rolling_72h_rainfall_mm >= 5.0
    assert bundle.is_storm_hazard is False
    assert bundle.observation.t_min < bundle.observation.t_max

    for f in bundle.forecasts:
        assert isinstance(f, DailyForecastSummary)
        assert f.temp_min_c <= f.temp_max_c
        assert 0.0 <= f.precipitation_probability <= 100.0


@pytest.mark.asyncio
async def test_weather_bundle_storm_hazard_24h_trigger():
    """Verify that 24-hour rainfall >= 50mm triggers the storm hazard flag."""
    bundle = await WeatherIngestionService.ingest_weather_bundle(
        latitude=17.50,
        longitude=78.50,
        simulated_live_rain_mm=55.0,  # >= 50mm threshold
    )

    assert bundle.rolling_24h_rainfall_mm == 55.0
    assert bundle.is_storm_hazard is True


@pytest.mark.asyncio
async def test_weather_bundle_storm_hazard_72h_trigger():
    """Verify that cumulative 72-hour rainfall >= 100mm triggers storm hazard."""
    bundle = await WeatherIngestionService.ingest_weather_bundle(
        latitude=17.50,
        longitude=78.50,
        simulated_live_rain_mm=45.0,
    )
    # If 24h is 45 and upcoming 48h exceeds 55mm -> rolling 72h >= 100
    if bundle.rolling_72h_rainfall_mm >= 100.0:
        assert bundle.is_storm_hazard is True


def test_parse_owm_forecast_json():
    """Verify OpenWeatherMap 3-hourly step aggregation into 5 daily summaries."""
    mock_owm_data = {
        "list": [
            {
                "dt_txt": "2026-08-01 06:00:00",
                "main": {"temp": 24.0},
                "rain": {"3h": 2.5},
                "pop": 0.4,
                "weather": [{"main": "Rain", "description": "light rain"}],
            },
            {
                "dt_txt": "2026-08-01 12:00:00",
                "main": {"temp": 31.0},
                "rain": {"3h": 4.0},
                "pop": 0.6,
                "weather": [{"main": "Rain", "description": "moderate rain"}],
            },
            {
                "dt_txt": "2026-08-02 06:00:00",
                "main": {"temp": 23.0},
                "rain": {"3h": 0.0},
                "pop": 0.1,
                "weather": [{"main": "Clear", "description": "clear sky"}],
            },
        ]
    }

    summaries = WeatherIngestionService._parse_owm_forecast_json(mock_owm_data)
    assert len(summaries) == 2

    day1 = summaries[0]
    assert day1.forecast_date == date(2026, 8, 1)
    assert day1.temp_min_c == 24.0
    assert day1.temp_max_c == 31.0
    assert day1.rainfall_mm == 6.5
    assert day1.precipitation_probability == 60.0
    assert day1.condition_code == "RAIN"

    day2 = summaries[1]
    assert day2.forecast_date == date(2026, 8, 2)
    assert day2.temp_min_c == 23.0
    assert day2.rainfall_mm == 0.0
    assert day2.condition_code == "CLEAR"

