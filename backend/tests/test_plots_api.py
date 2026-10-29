"""Integration Tests for Field Polygon Registration & PostGIS CRUD."""

import pytest
from app.models.profile import DeviceProfile


@pytest.fixture
def plot_test_farmer(db_session):
    profile = DeviceProfile(
        device_id="DEV-PLOT-TEST-001",
        farmer_name="Balaram Reddy",
        preferred_language="te",
        phone_number="+919848012345",
        kisan_id="PMK-998877",
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def test_create_and_list_plots(client, plot_test_farmer):
    """Verify field polygon registration, centroid auto-derivation, and area in hectares."""
    poly_payload = {
        "device_id": "DEV-PLOT-TEST-001",
        "name": "East Cotton Field",
        "survey_number": "142/A",
        "khasra_number": "K-88",
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
        "elevation_m": 260.0,
        "slope_percent": 1.8,
    }
    response = client.post("/api/v1/plots", json=poly_payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["id"] is not None
    assert data["name"] == "East Cotton Field"
    assert data["survey_number"] == "142/A"
    assert 17.5000 < data["centroid_lat"] < 17.5010
    assert 78.5000 < data["centroid_lon"] < 78.5010
    assert 0.95 <= data["area_hectares"] <= 1.05
    plot_id = data["id"]

    # Retrieve plot details
    get_resp = client.get(f"/api/v1/plots/{plot_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plot_id

    # List plots for device
    list_resp = client.get("/api/v1/plots?device_id=DEV-PLOT-TEST-001")
    assert list_resp.status_code == 200
    plots = list_resp.json()
    assert len(plots) == 1
    assert plots[0]["id"] == plot_id


def test_register_crop_cycle_and_telemetry(client, plot_test_farmer):
    """Verify adding crop cycles, groundwater telemetry, and Soil Health Card records."""
    poly_payload = {
        "device_id": "DEV-PLOT-TEST-001",
        "name": "South Paddy Field",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.40, 17.40],
                    [78.41, 17.40],
                    [78.41, 17.41],
                    [78.40, 17.41],
                    [78.40, 17.40],
                ]
            ],
        },
        "soil_texture": "Alfisol",
        "elevation_m": 220.0,
        "slope_percent": 0.8,
    }
    plot_resp = client.post("/api/v1/plots", json=poly_payload)
    plot_id = plot_resp.json()["id"]

    # 1. Register Crop Cycle
    cycle_payload = {
        "crop_name": "Paddy",
        "variety": "BPT-5204 (Samba Mahsuri)",
        "sowing_date": "2026-07-01",
        "growth_stage": "VEGETATIVE",
        "irrigation_method": "FLOOD",
        "expected_harvest_date": "2026-11-15",
    }
    cycle_resp = client.post(f"/api/v1/plots/{plot_id}/crop-cycle", json=cycle_payload)
    assert cycle_resp.status_code == 201
    assert cycle_resp.json()["crop_name"] == "Paddy"

    # 2. Add Groundwater Observation
    gw_payload = {
        "depth_mbgl": 9.4,
        "source_type": "HARDWARE_SENSOR",
    }
    gw_resp = client.post(f"/api/v1/plots/{plot_id}/groundwater", json=gw_payload)
    assert gw_resp.status_code == 201
    assert gw_resp.json()["depth_mbgl"] == 9.4

    # 3. Add Soil Health Card
    shc_payload = {
        "nitrogen_kg_ha": 155.0,
        "phosphorus_kg_ha": 16.5,
        "potassium_kg_ha": 190.0,
        "ph": 6.5,
        "organic_carbon_percent": 0.42,
        "source_type": "SOIL_HEALTH_CARD_API",
    }
    shc_resp = client.post(f"/api/v1/plots/{plot_id}/soil-health", json=shc_payload)
    assert shc_resp.status_code == 201
    assert shc_resp.json()["ph"] == 6.5
