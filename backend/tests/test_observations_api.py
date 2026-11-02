"""Integration Tests for Environmental Observations & Spatial Ingestion Endpoints (Milestone C)."""

import pytest
from app.models.profile import DeviceProfile


@pytest.fixture
def obs_test_farmer_and_plot(client, db_session):
    """Seed farmer profile and registered plot for observation testing."""
    profile = DeviceProfile(
        device_id="DEV-OBS-TEST-001",
        farmer_name="Ranganathan Pillai",
        preferred_language="hi",
        phone_number="+919444011223",
        kisan_id="PMK-OBS-4455",
    )
    db_session.add(profile)
    db_session.commit()

    poly_payload = {
        "device_id": "DEV-OBS-TEST-001",
        "name": "Cauvery Delta Plot",
        "survey_number": "12/4B",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.5000, 17.5000],
                    [78.50094, 17.5000],
                    [78.50094, 17.5009],
                    [78.5000, 17.5009],
                    [78.5000, 17.5000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 255.0,
        "slope_percent": 1.6,
    }
    resp = client.post("/api/v1/plots", json=poly_payload)
    assert resp.status_code == 201
    plot_id = resp.json()["id"]

    # Register crop cycle
    client.post(
        f"/api/v1/plots/{plot_id}/crop-cycle",
        json={
            "crop_name": "Cotton",
            "variety": "Bt-Cotton",
            "sowing_date": "2026-06-15",
            "growth_stage": "VEGETATIVE",
            "irrigation_method": "DRIP",
        },
    )

    return {"plot_id": plot_id, "device_id": "DEV-OBS-TEST-001"}


def test_get_plot_weather_history_and_forecasts(client, obs_test_farmer_and_plot):
    """Verify weather history ingestion, 5-day forecast window, and rolling cumulative rainfall."""
    plot_id = obs_test_farmer_and_plot["plot_id"]

    resp = client.get(f"/api/v1/plots/{plot_id}/weather/history")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["current_observation"] is not None
    assert data["current_observation"]["temp_min_c"] < data["current_observation"]["temp_max_c"]
    assert len(data["forecast_window"]) == 5
    assert len(data["historical_observations"]) >= 1
    assert data["is_storm_hazard"] is False


def test_get_plot_satellite_timeseries(client, obs_test_farmer_and_plot):
    """Verify Sentinel-2 NDVI/NDWI vegetation trajectory and vigor evaluation."""
    plot_id = obs_test_farmer_and_plot["plot_id"]

    resp = client.get(f"/api/v1/plots/{plot_id}/satellite/timeseries")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["latest"] is not None
    assert len(data["timeseries"]) >= 1
    assert -1.0 <= data["latest"]["mean_ndvi"] <= 1.0
    assert -1.0 <= data["latest"]["mean_ndwi"] <= 1.0
    assert data["vegetation_status"] in [
        "EXCELLENT_VIGOR",
        "MODERATE_VIGOR",
        "EARLY_EMERGENCE",
        "VEGETATION_STRESSED",
    ]


def test_get_plot_terrain_topography(client, obs_test_farmer_and_plot):
    """Verify Digital Elevation Model slope, TWI, and erosion hazard."""
    plot_id = obs_test_farmer_and_plot["plot_id"]

    resp = client.get(f"/api/v1/plots/{plot_id}/terrain")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["elevation_m"] > 0
    assert data["slope_percent"] == 1.6
    assert 0.8 <= data["slope_degrees"] <= 1.0
    assert data["twi"] > 0
    assert data["erosion_hazard"] == "STABLE"


def test_sync_plot_environmental_data(client, obs_test_farmer_and_plot):
    """Verify on-demand multi-layer environmental sync and hazard state integration."""
    plot_id = obs_test_farmer_and_plot["plot_id"]

    sync_resp = client.post(f"/api/v1/plots/{plot_id}/sync-environmental")
    assert sync_resp.status_code == 200, sync_resp.text
    data = sync_resp.json()

    assert data["plot_id"] == plot_id
    assert data["status"] == "SUCCESS"
    assert data["weather_synced"] is True
    assert data["satellite_synced"] is True
    assert data["groundwater_synced"] is True
    assert data["terrain_synced"] is True
    assert data["hazard_state"] == "NORMAL_MODE"


def test_sync_plot_environmental_storm_flood_override(client, obs_test_farmer_and_plot):
    """Verify that torrential rainfall (>= 50mm) transitions the hazard state to STORM_FLOOD_MODE."""
    plot_id = obs_test_farmer_and_plot["plot_id"]

    sync_resp = client.post(f"/api/v1/plots/{plot_id}/sync-environmental?simulated_rain_mm=65.0")
    assert sync_resp.status_code == 200
    data = sync_resp.json()

    assert data["hazard_state"] == "STORM_FLOOD_MODE"
    assert "STORM_FLOOD_MODE" in data["summary"]


def test_observation_endpoints_404_for_nonexistent_plot(client):
    """Verify that accessing observations for an unknown plot returns RFC 7807 404."""
    resp = client.get("/api/v1/plots/99999/weather/history")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status"] == 404
    assert "not found" in data["detail"].lower()

