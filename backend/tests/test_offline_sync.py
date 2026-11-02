"""Unit and Integration Tests for Offline Synchronization Engine (Milestone E)."""

from datetime import date, datetime, timezone
import uuid
import pytest
from app.models.profile import DeviceProfile
from app.services.crop_seed_service import seed_crops_if_empty


@pytest.fixture(autouse=True)
def setup_knowledge(db_session):
    """Seed crop catalog."""
    seed_crops_if_empty(db_session)


@pytest.fixture
def sync_test_setup(client, db_session):
    """Register farmer, plot, and active crop cycle for offline sync testing."""
    device_id = "DEV-SYNC-TEST-001"
    profile = DeviceProfile(
        device_id=device_id,
        farmer_name="Gangadhar Rao",
        preferred_language="te",
        phone_number="+919844007788",
        kisan_id="PMK-SYNC-5544",
    )
    db_session.add(profile)
    db_session.commit()

    plot_payload = {
        "device_id": device_id,
        "name": "Telangana Cotton Field",
        "survey_number": "15/A",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [79.0000, 18.0000],
                    [79.0015, 18.0000],
                    [79.0015, 18.0015],
                    [79.0000, 18.0015],
                    [79.0000, 18.0000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 310.0,
        "slope_percent": 1.2,
    }
    resp = client.post("/api/v1/plots", json=plot_payload)
    plot_id = resp.json()["id"]

    # Register crop cycle
    client.post(
        f"/api/v1/plots/{plot_id}/crop-cycle",
        json={
            "crop_name": "Cotton",
            "variety": "Bt Cotton RCH-2",
            "sowing_date": date.today().isoformat(),
            "growth_stage": "INITIAL",
            "irrigation_method": "DRIP",
        },
    )

    # Initialize roadmap and obtain checkpoint ID
    roadmap = client.get(f"/api/v1/plots/{plot_id}/roadmap").json()
    cp_id = roadmap["checkpoints"][0]["id"]

    return {"device_id": device_id, "plot_id": plot_id, "checkpoint_id": cp_id}


def test_offline_sync_batch_success(client, sync_test_setup):
    """Verify batch synchronization processes multiple offline actions successfully."""
    device_id = sync_test_setup["device_id"]
    plot_id = sync_test_setup["plot_id"]
    cp_id = sync_test_setup["checkpoint_id"]

    key1 = str(uuid.uuid4())
    key2 = str(uuid.uuid4())
    key3 = str(uuid.uuid4())

    batch_payload = {
        "device_id": device_id,
        "actions": [
            {
                "idempotency_key": key1,
                "action_type": "CHECKPOINT_COMPLETE",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"checkpoint_id": cp_id, "notes": "Seed treatment completed offline.", "status": "COMPLETED"},
            },
            {
                "idempotency_key": key2,
                "action_type": "LOG_IRRIGATION",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"plot_id": plot_id, "depth_mm": 35.0},
            },
            {
                "idempotency_key": key3,
                "action_type": "OFFLINE_NOTE",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"plot_id": plot_id, "note": "Checked soil moisture before irrigation."},
            },
        ],
    }

    resp = client.post("/api/v1/sync/batch", json=batch_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["device_id"] == device_id
    assert data["total_actions"] == 3
    assert data["applied"] == 3
    assert data["skipped"] == 0
    assert len(data["results"]) == 3
    assert all(r["status"] == "APPLIED" for r in data["results"])

    # Verify side-effect on database: checkpoint must now be completed
    roadmap = client.get(f"/api/v1/plots/{plot_id}/roadmap").json()
    cp = next(c for c in roadmap["checkpoints"] if c["id"] == cp_id)
    assert cp["status"] == "COMPLETED"
    assert "Seed treatment completed offline" in cp["notes"]


def test_offline_sync_strict_idempotency_duplicate_prevention(client, sync_test_setup):
    """Verify re-submitting identical sync batch returns DUPLICATE_SKIPPED with zero duplicate execution."""
    device_id = sync_test_setup["device_id"]
    plot_id = sync_test_setup["plot_id"]
    cp_id = sync_test_setup["checkpoint_id"]

    key_action = str(uuid.uuid4())

    batch_payload = {
        "device_id": device_id,
        "actions": [
            {
                "idempotency_key": key_action,
                "action_type": "CHECKPOINT_COMPLETE",
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"checkpoint_id": cp_id, "notes": "First submission."},
            }
        ],
    }

    # 1st Submission: Must be APPLIED
    resp1 = client.post("/api/v1/sync/batch", json=batch_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["applied"] == 1
    assert data1["skipped"] == 0
    assert data1["results"][0]["status"] == "APPLIED"

    # 2nd Submission with exact same idempotency_key: Must be DUPLICATE_SKIPPED
    resp2 = client.post("/api/v1/sync/batch", json=batch_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["applied"] == 0
    assert data2["skipped"] == 1
    assert data2["results"][0]["status"] == "DUPLICATE_SKIPPED"
    assert "previously applied" in data2["results"][0]["message"].lower()

