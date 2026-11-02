"""Unit and Integration Tests for Scientific Evaluation & MLOps Engine (Milestone F)."""

import pytest
from app.engines.evaluation_engine import EvaluationEngine
from app.models.profile import DeviceProfile
from app.services.crop_seed_service import seed_crops_if_empty
from app.services.soil_ingestion_service import SoilIngestionService


@pytest.fixture(autouse=True)
def setup_knowledge(db_session):
    """Seed crop catalog."""
    seed_crops_if_empty(db_session)


@pytest.fixture
def eval_test_plot(client, db_session):
    """Register farmer and plot for evaluation tests."""
    profile = DeviceProfile(
        device_id="DEV-EVAL-TEST-001",
        farmer_name="Dr. MS Swaminathan Scholar",
        preferred_language="en",
        phone_number="+919811002233",
        kisan_id="PMK-EVAL-7788",
    )
    db_session.add(profile)
    db_session.commit()

    plot_payload = {
        "device_id": "DEV-EVAL-TEST-001",
        "name": "Experimental Research Plot",
        "survey_number": "EX-1",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.0000, 17.0000],
                    [78.0015, 17.0000],
                    [78.0015, 17.0015],
                    [78.0000, 17.0015],
                    [78.0000, 17.0000],
                ]
            ],
        },
        "soil_texture": "Vertisol",
        "elevation_m": 450.0,
        "slope_percent": 1.2,
    }
    resp = client.post("/api/v1/plots", json=plot_payload)
    plot_id = resp.json()["id"]

    # Ingest soil record
    SoilIngestionService.ingest_soil_record(
        db=db_session,
        plot_id=plot_id,
        nitrogen_kg_ha=280.0,
        phosphorus_kg_ha=22.0,
        potassium_kg_ha=210.0,
        ph=7.4,
        organic_carbon_percent=0.65,
    )

    return {"plot_id": plot_id, "device_id": "DEV-EVAL-TEST-001"}


def test_scientific_lysimeter_benchmarks():
    """Verify FAO-56 Penman-Monteith ET0 passes empirical ICAR lysimeter benchmarks within 5% tolerance."""
    report = EvaluationEngine.evaluate_scientific_benchmarks()

    assert report.total_benchmarks >= 3
    assert report.all_passed is True
    assert report.passed_benchmarks == report.total_benchmarks
    assert report.max_relative_error_percent <= 5.0

    for result in report.results:
        assert result.passed is True
        assert result.relative_error_percent <= result.tolerance_percent


def test_plot_data_quality_evaluation(db_session, eval_test_plot):
    """Verify plot data quality scoring computes completeness, freshness, and uncertainty."""
    plot_id = eval_test_plot["plot_id"]
    report = EvaluationEngine.evaluate_plot_data_quality(db_session, plot_id=plot_id)

    assert report.plot_id == plot_id
    assert report.data_completeness_percent > 0.0
    assert report.sensor_freshness_hours >= 0.0
    assert 0.0 <= report.anomaly_score <= 1.0
    assert 0.0 <= report.agronomic_uncertainty_score <= 1.0
    assert report.overall_quality_grade in ("EXCELLENT", "GOOD", "ADEQUATE", "DEGRADED")
    assert "soil" in report.data_layer_status
    assert report.data_layer_status["soil"] == "MEASURED"


def test_scientific_benchmarks_api(client):
    """Verify GET /api/v1/evaluation/scientific-benchmarks endpoint."""
    resp = client.get("/api/v1/evaluation/scientific-benchmarks")
    assert resp.status_code == 200
    data = resp.json()

    assert data["all_passed"] is True
    assert data["total_benchmarks"] >= 3
    assert len(data["results"]) >= 3


def test_plot_quality_report_api(client, eval_test_plot):
    """Verify GET /api/v1/evaluation/plot/{plot_id}/quality-report endpoint."""
    plot_id = eval_test_plot["plot_id"]
    resp = client.get(f"/api/v1/evaluation/plot/{plot_id}/quality-report")
    assert resp.status_code == 200
    data = resp.json()

    assert data["plot_id"] == plot_id
    assert "overall_quality_grade" in data
    assert len(data["recommendations"]) >= 1


def test_plot_quality_report_not_found(client):
    """Verify 404 EntityNotFoundError for nonexistent plot."""
    resp = client.get("/api/v1/evaluation/plot/99999/quality-report")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"

