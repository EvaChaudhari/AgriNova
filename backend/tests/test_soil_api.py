"""Integration Tests for Soil Intelligence & ICAR Fertilizer Recommendation Endpoints (Milestone D)."""

import pytest
from app.models.profile import DeviceProfile
from app.services.crop_seed_service import seed_crops_if_empty


@pytest.fixture
def soil_test_plot(client, db_session):
    """Seed farmer profile and registered plot for soil testing."""
    seed_crops_if_empty(db_session)

    profile = DeviceProfile(
        device_id="DEV-SOIL-TEST-001",
        farmer_name="Savitribai Phule",
        preferred_language="mr",
        phone_number="+919822001122",
        kisan_id="PMK-SOIL-7788",
    )
    db_session.add(profile)
    db_session.commit()

    # Create 2.0 hectare plot
    poly_payload = {
        "device_id": "DEV-SOIL-TEST-001",
        "name": "Vidarbha Cotton Field",
        "survey_number": "45/2",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.0000, 20.5000],
                    [77.00188, 20.5000],
                    [77.00188, 20.5010],
                    [77.0000, 20.5010],
                    [77.0000, 20.5000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 310.0,
        "slope_percent": 1.2,
    }
    resp = client.post("/api/v1/plots", json=poly_payload)
    assert resp.status_code == 201
    plot_id = resp.json()["id"]

    # Register Cotton crop cycle
    client.post(
        f"/api/v1/plots/{plot_id}/crop-cycle",
        json={
            "crop_name": "Cotton",
            "variety": "Bt Cotton RCH-2",
            "sowing_date": "2026-06-20",
            "growth_stage": "VEGETATIVE",
            "irrigation_method": "DRIP",
        },
    )

    return {"plot_id": plot_id, "device_id": "DEV-SOIL-TEST-001"}


def test_ingest_soil_health_card(client, soil_test_plot):
    """Verify ingestion of Soil Health Card lab results and ICAR fertility classification."""
    plot_id = soil_test_plot["plot_id"]
    payload = {
        "nitrogen_kg_ha": 210.0,
        "phosphorus_kg_ha": 11.5,
        "potassium_kg_ha": 175.0,
        "ph": 8.7,
        "organic_carbon_percent": 0.42,
        "source_type": "SOIL_HEALTH_CARD_MANUAL",
        "tested_date": "2026-07-01",
    }

    resp = client.post(f"/api/v1/plots/{plot_id}/soil", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["nitrogen_kg_ha"] == 210.0
    assert data["ph"] == 8.7
    assert data["source_type"] == "SOIL_HEALTH_CARD_MANUAL"

    rating = data["rating"]
    assert rating["nitrogen_rating"] == "LOW"
    assert rating["phosphorus_rating"] == "LOW"
    assert rating["potassium_rating"] == "MEDIUM"
    assert rating["organic_carbon_rating"] == "LOW"
    assert rating["ph_classification"] == "SODIC"
    assert "gypsum" in rating["soil_amendment_directive"].lower()
    assert 0.0 <= rating["soil_health_index"] <= 100.0


def test_get_plot_soil_rating_fallback(client, soil_test_plot):
    """Verify fetching soil rating when no test has been recorded yet falls back cleanly to regional baseline."""
    plot_id = soil_test_plot["plot_id"]
    resp = client.get(f"/api/v1/plots/{plot_id}/soil/rating")
    assert resp.status_code == 200
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["nitrogen_kg_ha"] > 0
    assert data["ph"] > 0
    assert data["rating"]["nitrogen_rating"] in ("LOW", "MEDIUM", "HIGH")


def test_compute_fertilizer_recommendation_explicit_target(client, soil_test_plot):
    """Verify STCR fertilizer calculation with explicit target yield and crop name."""
    plot_id = soil_test_plot["plot_id"]

    # Ingest soil test first
    client.post(
        f"/api/v1/plots/{plot_id}/soil",
        json={
            "nitrogen_kg_ha": 200.0,
            "phosphorus_kg_ha": 15.0,
            "potassium_kg_ha": 180.0,
            "ph": 7.5,
            "organic_carbon_percent": 0.55,
        },
    )

    req_payload = {
        "target_yield_q_ha": 25.0,
        "crop_name": "Cotton",
    }
    resp = client.post(f"/api/v1/plots/{plot_id}/fertilizer-recommendation", json=req_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["crop_name"] == "Cotton"
    assert data["target_yield_q_ha"] == 25.0
    assert data["recommended_n_kg_ha"] > 0
    assert data["recommended_p_kg_ha"] > 0
    assert data["recommended_k_kg_ha"] > 0

    # Bag equivalents
    assert data["total_dap_bags_50kg"] > 0
    assert data["total_urea_bags_50kg"] > 0
    assert data["total_mop_bags_50kg"] > 0

    # Field area scaling
    assert data["field_area_hectares"] > 0
    assert data["field_total_dap_bags"] > 0
    assert data["field_total_urea_bags"] > 0
    assert data["field_total_mop_bags"] > 0

    # Split schedule
    assert len(data["split_schedule"]) == 3
    stages = [item["growth_stage"] for item in data["split_schedule"]]
    assert "BASAL_SOWING" in stages
    assert "VEGETATIVE_STAGE" in stages
    assert "FLOWERING_STAGE" in stages


def test_compute_fertilizer_recommendation_auto_detect_crop_cycle(client, soil_test_plot):
    """Verify auto-detection of crop name from active crop cycle when payload crop_name is omitted."""
    plot_id = soil_test_plot["plot_id"]

    # Empty payload defaults to active cycle's crop (Cotton) and default target yield
    resp = client.post(f"/api/v1/plots/{plot_id}/fertilizer-recommendation", json={})
    assert resp.status_code == 200
    data = resp.json()

    assert data["crop_name"] == "Cotton"
    assert data["target_yield_q_ha"] == 25.0
    assert data["recommended_n_kg_ha"] > 0


def test_soil_api_not_found(client):
    """Verify RFC 7807 problem details on nonexistent plot ID."""
    resp = client.get("/api/v1/plots/99999/soil/rating")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"
    assert body["status"] == 404
    assert "not found" in body["detail"].lower()


def test_soil_api_validation_error(client, soil_test_plot):
    """Verify validation constraint rejection for out-of-bounds pH."""
    plot_id = soil_test_plot["plot_id"]
    # pH 15 is unphysical
    resp = client.post(f"/api/v1/plots/{plot_id}/soil", json={"ph": 15.0})
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == 422
    assert "validation" in body["title"].lower()
