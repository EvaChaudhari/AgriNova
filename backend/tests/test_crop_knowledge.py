"""Integration Tests for Agronomic Crop Knowledge Base Endpoints (Milestone D)."""

import pytest
from app.services.crop_seed_service import seed_crops_if_empty


@pytest.fixture(autouse=True)
def seed_knowledge_base(db_session):
    """Ensure baseline crops and varieties are seeded for every test."""
    seed_crops_if_empty(db_session)


def test_seed_crops_idempotent(db_session):
    """Verify that calling seed_crops_if_empty multiple times does not create duplicates."""
    count1 = seed_crops_if_empty(db_session)
    count2 = seed_crops_if_empty(db_session)
    assert count1 == 8
    assert count2 == 8


def test_list_crops_all(client):
    """Verify listing all active staple crops."""
    resp = client.get("/api/v1/crops")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    names = [c["name"] for c in data]
    assert "Cotton" in names
    assert "Paddy" in names
    assert "Wheat" in names
    assert "Chickpea" in names


def test_list_crops_filtered_by_season(client):
    """Verify filtering crops by agricultural season."""
    # Kharif
    resp_kharif = client.get("/api/v1/crops?season=KHARIF")
    assert resp_kharif.status_code == 200
    kharif_crops = [c["name"] for c in resp_kharif.json()]
    assert "Cotton" in kharif_crops
    assert "Paddy" in kharif_crops
    assert "Wheat" not in kharif_crops

    # Rabi
    resp_rabi = client.get("/api/v1/crops?season=RABI")
    assert resp_rabi.status_code == 200
    rabi_crops = [c["name"] for c in resp_rabi.json()]
    assert "Wheat" in rabi_crops
    assert "Mustard" in rabi_crops
    assert "Cotton" not in rabi_crops


def test_list_crops_filtered_by_category(client):
    """Verify filtering crops by agronomic category."""
    # Pulses
    resp = client.get("/api/v1/crops?category=PULSE")
    assert resp.status_code == 200
    pulses = resp.json()
    assert len(pulses) == 1
    assert pulses[0]["name"] == "Chickpea"

    # Cereals
    resp_cereal = client.get("/api/v1/crops?category=CEREAL")
    assert resp_cereal.status_code == 200
    cereals = [c["name"] for c in resp_cereal.json()]
    assert "Wheat" in cereals
    assert "Paddy" in cereals
    assert "Maize" in cereals


def test_get_crop_detail_dossier(client):
    """Verify comprehensive crop dossier endpoint with varieties, stages, STCR benchmark, and pests."""
    # Find Cotton ID
    crops = client.get("/api/v1/crops").json()
    cotton = next(c for c in crops if c["name"] == "Cotton")
    cotton_id = cotton["id"]

    resp = client.get(f"/api/v1/crops/{cotton_id}")
    assert resp.status_code == 200
    dossier = resp.json()

    assert dossier["name"] == "Cotton"
    assert dossier["scientific_name"] == "Gossypium hirsutum"
    assert len(dossier["varieties"]) >= 2
    assert any("Bt Cotton" in v["variety_name"] for v in dossier["varieties"])

    assert len(dossier["growth_stages"]) == 4
    stage_names = [s["stage_name"] for s in dossier["growth_stages"]]
    assert "INITIAL" in stage_names
    assert "VEGETATIVE" in stage_names
    assert "FLOWERING" in stage_names
    assert "MATURITY" in stage_names

    # STCR benchmark
    bm = dossier["nutrient_benchmark"]
    assert bm is not None
    assert bm["stcr_a_n"] == 4.40
    assert bm["max_n_kg_ha"] == 150.0

    # Pest profiles
    assert len(dossier["pest_profiles"]) >= 1
    assert any("Pink Bollworm" in p["pest_name"] for p in dossier["pest_profiles"])


def test_get_stage_at_das_flowering(client):
    """Verify stage-at-DAS resolution dynamically identifies active stage, Kc, and pest threats."""
    crops = client.get("/api/v1/crops").json()
    cotton = next(c for c in crops if c["name"] == "Cotton")
    cotton_id = cotton["id"]

    # At DAS 65 (Cotton flowering is 61-105 DAS)
    resp = client.get(f"/api/v1/crops/{cotton_id}/stage-at-das?das=65")
    assert resp.status_code == 200
    data = resp.json()

    assert data["crop_name"] == "Cotton"
    assert data["das"] == 65
    assert data["current_stage"] == "FLOWERING"
    assert data["kc"] == 1.20
    assert data["rooting_depth_m"] == 1.10
    assert data["critical_water_stage"] is True
    assert data["days_remaining_in_stage"] == (105 - 65)

    # Pest threat for flowering stage
    pests = [p["pest_name"] for p in data["stage_pest_threats"]]
    assert any("Pink Bollworm" in name for name in pests)


def test_get_stage_at_das_clamping(client):
    """Verify out-of-range DAS clamps gracefully to INITIAL or MATURITY."""
    crops = client.get("/api/v1/crops").json()
    wheat = next(c for c in crops if c["name"] == "Wheat")
    wheat_id = wheat["id"]

    # DAS 0 clamps to INITIAL
    resp_init = client.get(f"/api/v1/crops/{wheat_id}/stage-at-das?das=0")
    assert resp_init.status_code == 200
    assert resp_init.json()["current_stage"] == "INITIAL"

    # DAS 200 (Wheat duration is 120 days) clamps to MATURITY
    resp_mat = client.get(f"/api/v1/crops/{wheat_id}/stage-at-das?das=200")
    assert resp_mat.status_code == 200
    assert resp_mat.json()["current_stage"] == "MATURITY"


def test_get_crop_not_found(client):
    """Verify RFC 7807 problem details response for nonexistent crop."""
    resp = client.get("/api/v1/crops/99999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"
    assert body["status"] == 404
    assert "not found" in body["detail"].lower()
