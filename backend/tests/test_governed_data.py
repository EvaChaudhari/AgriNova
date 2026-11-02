"""Unit and Integration Tests for DPDP-Compliant Governed Data Products (Milestone F)."""

from datetime import date
import pytest
from app.models.auth import User
from app.models.consent import ConsentRecord
from app.models.plot import CropCycle, Farm, FarmPlot
from app.models.profile import DeviceProfile
from app.services.governed_data_service import GovernedDataService


@pytest.fixture
def governed_data_setup(client, db_session):
    """Seed two farmers: Farmer A with granted consent, Farmer B with revoked consent."""
    # Farmer A: Consented
    user_a = User(
        phone_number="+919800000001",
        full_name="Consented Farmer",
        hashed_pin="dummy",
        is_active=True,
    )
    db_session.add(user_a)
    db_session.flush()

    farm_a = Farm(user_id=user_a.id, name="Consented Farm", district="Yavatmal", total_area_hectares=2.5)
    db_session.add(farm_a)
    db_session.flush()

    plot_a = FarmPlot(
        farm_id=farm_a.id,
        user_id=user_a.id,
        name="Consented Cotton Field",
        boundary="POLYGON((78.0 20.0, 78.01 20.0, 78.01 20.01, 78.0 20.01, 78.0 20.0))",
        centroid_lat=20.005,
        centroid_lon=78.005,
        area_hectares=2.5,
        soil_texture="Vertisol",
    )
    db_session.add(plot_a)
    db_session.flush()

    cycle_a = CropCycle(plot_id=plot_a.id, crop_name="Cotton", variety="Bt-Cotton RCH-2", sowing_date=date(2026, 6, 15))
    db_session.add(cycle_a)

    # Explicit GRANTED consent
    consent_a = ConsentRecord(
        user_id=user_a.id,
        purpose="ANALYTICS",
        status="GRANTED",
    )
    db_session.add(consent_a)

    # Farmer B: Revoked Consent
    user_b = User(
        phone_number="+919800000002",
        full_name="Revoked Farmer",
        hashed_pin="dummy",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.flush()

    farm_b = Farm(user_id=user_b.id, name="Revoked Farm", district="Yavatmal", total_area_hectares=4.0)
    db_session.add(farm_b)
    db_session.flush()

    plot_b = FarmPlot(
        farm_id=farm_b.id,
        user_id=user_b.id,
        name="Revoked Wheat Field",
        boundary="POLYGON((78.0 20.0, 78.01 20.0, 78.01 20.01, 78.0 20.01, 78.0 20.0))",
        centroid_lat=20.005,
        centroid_lon=78.005,
        area_hectares=4.0,
        soil_texture="Vertisol",
    )
    db_session.add(plot_b)
    db_session.flush()

    cycle_b = CropCycle(plot_id=plot_b.id, crop_name="Wheat", variety="HD-2967", sowing_date=date(2026, 11, 1))
    db_session.add(cycle_b)

    # Explicit REVOKED consent
    consent_b = ConsentRecord(
        user_id=user_b.id,
        purpose="ANALYTICS",
        status="REVOKED",
    )
    db_session.add(consent_b)

    db_session.commit()
    return {"plot_a_id": plot_a.id, "plot_b_id": plot_b.id}


def test_dpdp_consent_enforcement_in_fpo_summary(db_session, governed_data_setup):
    """Verify only consented plots are included and revoked plots are excluded under DPDP Act."""
    report = GovernedDataService.get_fpo_crop_summary(db_session, district="Yavatmal")

    # Confirms consented plot A is included
    assert report.total_consented_plots >= 1
    crop_names = [c.crop_name for c in report.crops]
    assert "Cotton" in crop_names

    # Confirms revoked plot B (Wheat) is strictly excluded
    assert "Wheat" not in crop_names
    for item in report.crops:
        assert item.crop_name != "Wheat"

    # Confirms zero PII in report output
    assert hasattr(report, "crops")
    report_dict = report.model_dump()
    assert "phone_number" not in str(report_dict)
    assert "full_name" not in str(report_dict)


def test_fpo_crop_summary_api(client, governed_data_setup):
    """Verify GET /api/v1/governed/fpo/crop-summary endpoint."""
    resp = client.get("/api/v1/governed/fpo/crop-summary?district=Yavatmal")
    assert resp.status_code == 200
    data = resp.json()

    assert data["district"] == "Yavatmal"
    assert data["total_consented_plots"] >= 1
    assert "DPDP" in data["data_anonymization_standard"]


def test_parametric_insurance_drought_index_api(client):
    """Verify GET /api/v1/governed/insurance/drought-index endpoint."""
    resp = client.get("/api/v1/governed/insurance/drought-index")
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["blocks"]) >= 2
    assert "payout_triggered_blocks_count" in data

    for block in data["blocks"]:
        assert 0.0 <= block["drought_risk_score"] <= 100.0
        assert block["drought_trigger_status"] in ("NORMAL", "WATCH", "TRIGGER_PAYOUT")
