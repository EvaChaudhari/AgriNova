"""Unit and Integration Tests for Crop Suitability Planner Engine (Milestone E)."""

import pytest
from app.engines.crop_planner import CropPlannerEngine
from app.models.profile import DeviceProfile
from app.services.crop_seed_service import seed_crops_if_empty


@pytest.fixture(autouse=True)
def setup_knowledge(db_session):
    """Seed crop catalog before planner evaluation."""
    seed_crops_if_empty(db_session)


@pytest.fixture
def planner_test_plot(client, db_session):
    """Register farmer and test plot with Vertisol soil."""
    profile = DeviceProfile(
        device_id="DEV-PLAN-TEST-001",
        farmer_name="Bhimrao Patil",
        preferred_language="mr",
        phone_number="+919823004455",
        kisan_id="PMK-PLAN-1234",
    )
    db_session.add(profile)
    db_session.commit()

    plot_payload = {
        "device_id": "DEV-PLAN-TEST-001",
        "name": "Deccan Black Soil Field",
        "survey_number": "88/1",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [76.0000, 19.5000],
                    [76.0015, 19.5000],
                    [76.0015, 19.5015],
                    [76.0000, 19.5015],
                    [76.0000, 19.5000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 420.0,
        "slope_percent": 1.4,
    }
    resp = client.post("/api/v1/plots", json=plot_payload)
    assert resp.status_code == 201
    plot_id = resp.json()["id"]

    # Register crop cycle with drip irrigation
    client.post(
        f"/api/v1/plots/{plot_id}/crop-cycle",
        json={
            "crop_name": "Cotton",
            "variety": "Bt Cotton RCH-2",
            "sowing_date": "2026-06-15",
            "growth_stage": "INITIAL",
            "irrigation_method": "DRIP",
        },
    )

    return {"plot_id": plot_id, "device_id": "DEV-PLAN-TEST-001"}


def test_crop_planner_vertisol_kharif_optimal(db_session):
    """Verify Vertisol Kharif evaluation identifies Cotton and Soybean as optimal."""
    results = CropPlannerEngine.evaluate_crop_suitability(
        db=db_session,
        soil_texture="Vertisol",
        soil_ph=7.4,
        groundwater_depth_mbgl=10.0,
        irrigation_method="DRIP",
        season="KHARIF",
    )

    assert len(results) > 0
    top_crop = results[0]
    assert top_crop.crop_name in ("Cotton", "Soybean")
    assert top_crop.suitability_score >= 75.0
    assert top_crop.risk_category == "OPTIMAL"
    assert len(top_crop.recommended_varieties) >= 1


def test_crop_planner_penalizes_thirsty_crops_under_drought(db_session):
    """Verify deep groundwater and rainfed farming severely penalize Sugarcane and Paddy."""
    results = CropPlannerEngine.evaluate_crop_suitability(
        db=db_session,
        soil_texture="Sandy Loam",
        soil_ph=7.2,
        groundwater_depth_mbgl=22.0,  # Severely depleted water table
        irrigation_method="RAINFED",
        season="KHARIF",
    )

    # Sugarcane or Paddy must receive severe water penalty
    for item in results:
        if item.crop_name in ("Sugarcane", "Paddy"):
            assert item.suitability_score < 50.0
            assert item.risk_category == "HIGH_RISK_DROUGHT"
            assert any("groundwater" in f.lower() or "perennial" in f.lower() for f in item.limiting_factors)


def test_crop_planner_rabi_drought_tolerant(db_session):
    """Verify low-water Rabi pulses (Chickpea, Mustard) achieve high suitability."""
    results = CropPlannerEngine.evaluate_crop_suitability(
        db=db_session,
        soil_texture="Vertisol",
        soil_ph=7.5,
        groundwater_depth_mbgl=14.0,
        irrigation_method="FLOOD",
        season="RABI",
    )

    rabi_names = [r.crop_name for r in results]
    assert "Chickpea" in rabi_names
    assert "Wheat" in rabi_names
    assert "Mustard" in rabi_names

    chickpea = next(r for r in results if r.crop_name == "Chickpea")
    assert chickpea.suitability_score >= 70.0


def test_crop_planner_category_filter(db_session):
    """Verify category filtering isolates specific crop classifications."""
    pulse_results = CropPlannerEngine.evaluate_crop_suitability(
        db=db_session,
        soil_texture="Alluvial",
        soil_ph=7.0,
        groundwater_depth_mbgl=8.0,
        irrigation_method="SPRINKLER",
        season="RABI",
        preferred_category="PULSE",
    )

    assert len(pulse_results) == 1
    assert pulse_results[0].crop_name == "Chickpea"
    assert pulse_results[0].category == "PULSE"


def test_planner_api_endpoint(client, planner_test_plot):
    """Verify POST /api/v1/planner/recommend-crops endpoint execution."""
    plot_id = planner_test_plot["plot_id"]
    payload = {
        "plot_id": plot_id,
        "season": "KHARIF",
    }
    resp = client.post("/api/v1/planner/recommend-crops", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["season"] == "KHARIF"
    assert len(data["recommendations"]) >= 2
    top = data["recommendations"][0]
    assert "crop_name" in top
    assert "suitability_score" in top
    assert "risk_category" in top


def test_planner_api_plot_not_found(client):
    """Verify 404 EntityNotFoundError for nonexistent plot."""
    resp = client.post("/api/v1/planner/recommend-crops", json={"plot_id": 99999})
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"
    assert "not found" in body["detail"].lower()

