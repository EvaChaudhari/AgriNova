"""Unit and Integration Tests for Crop Roadmap & Checkpoint Engine (Milestone E)."""

from datetime import date, timedelta
import pytest
from app.engines.roadmap_engine import RoadmapEngine
from app.models.profile import DeviceProfile
from app.models.plot import CropCycle, FarmPlot
from app.services.crop_seed_service import seed_crops_if_empty


@pytest.fixture(autouse=True)
def setup_knowledge(db_session):
    """Seed crop catalog."""
    seed_crops_if_empty(db_session)


@pytest.fixture
def roadmap_test_plot(client, db_session):
    """Register farmer, plot, and active Cotton crop cycle."""
    profile = DeviceProfile(
        device_id="DEV-ROAD-TEST-001",
        farmer_name="Shrikant Shinde",
        preferred_language="mr",
        phone_number="+919833005566",
        kisan_id="PMK-ROAD-9988",
    )
    db_session.add(profile)
    db_session.commit()

    plot_payload = {
        "device_id": "DEV-ROAD-TEST-001",
        "name": "Khandesh Cotton Farm",
        "survey_number": "102/3",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [75.5000, 20.8000],
                    [75.5015, 20.8000],
                    [75.5015, 20.8015],
                    [75.5000, 20.8015],
                    [75.5000, 20.8000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 290.0,
        "slope_percent": 1.1,
    }
    resp = client.post("/api/v1/plots", json=plot_payload)
    assert resp.status_code == 201
    plot_id = resp.json()["id"]

    # Register crop cycle sown 40 days ago (currently vegetative)
    sowing_date = date.today() - timedelta(days=40)
    client.post(
        f"/api/v1/plots/{plot_id}/crop-cycle",
        json={
            "crop_name": "Cotton",
            "variety": "Bt Cotton RCH-2",
            "sowing_date": sowing_date.isoformat(),
            "growth_stage": "VEGETATIVE",
            "irrigation_method": "DRIP",
        },
    )

    return {"plot_id": plot_id, "device_id": "DEV-ROAD-TEST-001", "sowing_date": sowing_date}


def test_roadmap_creation_and_structure(db_session, roadmap_test_plot):
    """Verify automatic milestone generation generates 6 chronological checkpoints."""
    plot_id = roadmap_test_plot["plot_id"]
    cycle = db_session.query(CropCycle).filter(CropCycle.plot_id == plot_id).first()

    roadmap = RoadmapEngine.get_or_create_roadmap(db_session, plot_id=plot_id, crop_cycle=cycle)

    assert roadmap.plot_id == plot_id
    assert roadmap.crop_name == "Cotton"
    assert roadmap.total_checkpoints == 6
    assert len(roadmap.checkpoints) == 6

    # Verify chronological sequence
    das_list = [cp.target_day_after_sowing for cp in roadmap.checkpoints]
    assert das_list == sorted(das_list)
    assert das_list[0] == 0  # Sowing
    assert das_list[-1] > 100  # Maturity

    # At 40 DAS, current stage should be VEGETATIVE
    assert roadmap.current_stage == "VEGETATIVE"


def test_complete_and_defer_checkpoint(db_session, roadmap_test_plot):
    """Verify completing a checkpoint updates completed counter and logs completion date."""
    plot_id = roadmap_test_plot["plot_id"]
    cycle = db_session.query(CropCycle).filter(CropCycle.plot_id == plot_id).first()
    roadmap = RoadmapEngine.get_or_create_roadmap(db_session, plot_id=plot_id, crop_cycle=cycle)

    first_cp = roadmap.checkpoints[0]
    assert first_cp.status == "PENDING"

    # Complete first checkpoint
    updated = RoadmapEngine.complete_checkpoint(
        db_session,
        checkpoint_id=first_cp.id,
        notes="Applied Trichoderma viride seed treatment @ 4g/kg seed.",
        status="COMPLETED",
    )
    assert updated.status == "COMPLETED"
    assert updated.completed_at is not None
    assert "Trichoderma" in updated.notes
    assert roadmap.completed_checkpoints == 1

    # Defer second checkpoint
    second_cp = roadmap.checkpoints[1]
    deferred = RoadmapEngine.complete_checkpoint(
        db_session,
        checkpoint_id=second_cp.id,
        notes="Delayed due to unexpected rain.",
        status="DEFERRED",
    )
    assert deferred.status == "DEFERRED"


def test_get_plot_roadmap_api(client, roadmap_test_plot):
    """Verify GET /api/v1/plots/{plot_id}/roadmap returns structured roadmap response."""
    plot_id = roadmap_test_plot["plot_id"]
    resp = client.get(f"/api/v1/plots/{plot_id}/roadmap")
    assert resp.status_code == 200
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert data["crop_name"] == "Cotton"
    assert data["days_after_sowing"] == 40
    assert data["current_stage"] == "VEGETATIVE"
    assert data["total_checkpoints"] == 6
    assert len(data["checkpoints"]) == 6
    assert data["progress_percent"] == 0.0


def test_complete_checkpoint_api(client, roadmap_test_plot):
    """Verify POST /api/v1/plots/{plot_id}/checkpoints/{checkpoint_id}/complete endpoint."""
    plot_id = roadmap_test_plot["plot_id"]

    # Fetch roadmap to get a checkpoint ID
    roadmap = client.get(f"/api/v1/plots/{plot_id}/roadmap").json()
    cp_id = roadmap["checkpoints"][0]["id"]

    payload = {
        "notes": "Completed manual weed removal and soil aeration.",
        "status": "COMPLETED",
    }
    resp = client.post(f"/api/v1/plots/{plot_id}/checkpoints/{cp_id}/complete", json=payload)
    assert resp.status_code == 200
    cp_data = resp.json()

    assert cp_data["id"] == cp_id
    assert cp_data["status"] == "COMPLETED"
    assert "manual weed" in cp_data["notes"]

    # Verify roadmap progress is updated
    updated_roadmap = client.get(f"/api/v1/plots/{plot_id}/roadmap").json()
    assert updated_roadmap["completed_checkpoints"] == 1
    assert updated_roadmap["progress_percent"] > 0.0


def test_roadmap_api_not_found(client):
    """Verify RFC 7807 problem details on nonexistent plot ID."""
    resp = client.get("/api/v1/plots/99999/roadmap")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"
    assert "not found" in body["detail"].lower()

