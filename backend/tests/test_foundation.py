"""Unit & Integration Tests for Milestone A: Foundation and Observability.

Verifies:
1. /health liveness probe succeeds independently of database health.
2. /ready readiness probe succeeds when DB and storage are healthy.
3. /ready readiness probe returns 503 when the database fails.
4. Validation errors return consistent RFC 7807 problem details.
5. Unexpected exceptions mask internal stack traces and secrets from clients.
6. Correlation IDs are generated, propagated, and returned in headers.
7. Legacy / and /healthz endpoints maintain backward compatibility.
"""

from unittest.mock import MagicMock
import pytest
from fastapi import APIRouter
from sqlalchemy.exc import OperationalError
from app.main import app
from app.core.database import get_db
from app.core.exceptions import (
    AgriNovaException,
    EntityNotFoundError,
    HydrologicalCalculationError,
    HazardStateViolationError,
)

# Router for foundation exception testing
diagnostics_router = APIRouter(prefix="/api/test-foundation", tags=["Testing"])


@diagnostics_router.get("/trigger-unhandled-error")
def trigger_unhandled():
    raise RuntimeError("Critical internal secret: db_password_xyz123 should never leak!")


@diagnostics_router.get("/trigger-domain-error")
def trigger_domain():
    raise HazardStateViolationError(
        detail="Cannot apply fertilizer when STORM_FLOOD_MODE is active.",
    )


@diagnostics_router.get("/trigger-not-found")
def trigger_not_found():
    raise EntityNotFoundError(detail="FarmPlot with ID 9999 was not found.")


app.include_router(diagnostics_router)


def test_health_liveness_succeeds_without_database(client):
    """Verify /health confirms process is alive even if database dependency is broken."""

    def broken_db():
        raise OperationalError("Connection refused to database", None, None)

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pass"
        assert "service" in data
        assert "timestamp" in data
        assert "X-Correlation-ID" in response.headers
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_ready_probe_succeeds_when_healthy(client):
    """Verify /ready probe returns 200 and checks pass when DB and storage are available."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pass"
    assert data["checks"]["database"] == "pass"
    assert data["checks"]["storage"] == "pass"
    assert "X-Correlation-ID" in response.headers


def test_ready_probe_fails_503_when_database_unavailable(client):
    """Verify /ready probe returns 503 and flags database failure without exposing internal details."""
    mock_session = MagicMock()
    mock_session.execute.side_effect = OperationalError("connection timeout to postgres://user:secret@db:5432", None, None)

    def failing_db():
        yield mock_session

    app.dependency_overrides[get_db] = failing_db
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "fail"
        assert data["checks"]["database"] == "fail"
        # Must not expose the database credentials or connection string
        assert "secret" not in response.text
        assert "postgres://" not in response.text
        assert "One or more required subsystem readiness checks failed." in data["detail"]
        assert "X-Correlation-ID" in response.headers
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_validation_errors_rfc7807_problem_details(client):
    """Verify invalid payloads trigger RFC 7807 problem details with invalid_params list."""
    # Send invalid plot creation payload missing required fields and with bad polygon
    invalid_payload = {
        "device_id": "TEST-DEV",
        # "name" missing
        "boundary": {"type": "InvalidGeometry"},
    }
    response = client.post("/api/v1/plots", json=invalid_payload)
    assert response.status_code == 422
    assert response.headers.get("content-type") == "application/problem+json"

    data = response.json()
    assert data["type"] == "urn:agrinova:error:validation-error"
    assert data["title"] == "Request Validation Failed"
    assert data["status"] == 422
    assert data["instance"] == "/api/v1/plots"
    assert "correlation_id" in data
    assert isinstance(data["invalid_params"], list)
    assert len(data["invalid_params"]) > 0

    # Verify field names appear in invalid_params
    field_names = [p["name"] for p in data["invalid_params"]]
    assert any("name" in f for f in field_names)


def test_unexpected_exceptions_mask_internal_secrets():
    """Verify unhandled exceptions return 500 without leaking stack traces or internal secrets."""
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as no_raise_client:
        response = no_raise_client.get("/api/test-foundation/trigger-unhandled-error")
        assert response.status_code == 500
        assert response.headers.get("content-type") == "application/problem+json"

        data = response.json()
        assert data["type"] == "urn:agrinova:error:internal-server-error"
        assert data["status"] == 500
        assert "An unexpected internal server error occurred" in data["detail"]

        # Verify that the sensitive internal exception string is NOT in the response
        assert "db_password_xyz123" not in response.text
        assert "Traceback" not in response.text
        assert "correlation_id" in data


def test_domain_exceptions_rfc7807(client):
    """Verify agricultural domain exceptions return properly typed RFC 7807 problem details."""
    response = client.get("/api/test-foundation/trigger-domain-error")
    assert response.status_code == 400
    assert response.headers.get("content-type") == "application/problem+json"

    data = response.json()
    assert data["type"] == "urn:agrinova:error:hazard-state-violation"
    assert data["title"] == "Hazard Safety Restriction Violation"
    assert data["status"] == 400
    assert "Cannot apply fertilizer when STORM_FLOOD_MODE is active." in data["detail"]


def test_entity_not_found_exception_rfc7807(client):
    """Verify EntityNotFoundError returns 404 RFC 7807 problem details."""
    response = client.get("/api/test-foundation/trigger-not-found")
    assert response.status_code == 404
    assert response.headers.get("content-type") == "application/problem+json"

    data = response.json()
    assert data["type"] == "urn:agrinova:error:not-found"
    assert data["status"] == 404
    assert "FarmPlot with ID 9999 was not found." in data["detail"]


def test_correlation_id_generation_and_propagation(client):
    """Verify correlation ID is auto-generated if missing, or preserved if supplied."""
    # 1. No correlation ID header provided -> generated
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    cid1 = resp1.headers.get("X-Correlation-ID")
    assert cid1 is not None
    assert len(cid1) >= 16

    # 2. Custom correlation ID provided -> preserved
    custom_cid = "agrinova-audit-trace-uuid-999"
    resp2 = client.get("/health", headers={"X-Correlation-ID": custom_cid})
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Correlation-ID") == custom_cid


def test_legacy_healthz_and_root_endpoints(client):
    """Verify backward compatibility of legacy / and /healthz endpoints."""
    # GET /
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["status"] == "healthy"
    assert "X-Correlation-ID" in root_resp.headers

    # GET /healthz
    healthz_resp = client.get("/healthz")
    assert healthz_resp.status_code == 200
    assert healthz_resp.json()["status"] == "ok"
    assert "X-Correlation-ID" in healthz_resp.headers
