"""Unit & Integration Tests for Farmer Identity, Authentication, and Consent (Milestone B)."""

from datetime import timedelta
import pytest

from app.core.exceptions import UnauthorizedAccessError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_pin_or_password,
    verify_pin_or_password,
)


def test_pin_hashing_and_verification():
    """Verify PBKDF2-HMAC-SHA256 numeric PIN hashing and constant-time verification."""
    pin = "4321"
    hashed = hash_pin_or_password(pin)

    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert verify_pin_or_password(pin, hashed) is True
    assert verify_pin_or_password("0000", hashed) is False
    assert verify_pin_or_password("", hashed) is False
    assert verify_pin_or_password(pin, "invalid$format") is False
    assert verify_pin_or_password(pin, "") is False

    with pytest.raises(ValueError):
        hash_pin_or_password("")


def test_jwt_token_lifecycle_and_expiry():
    """Verify JWT token encoding, decoding, custom claims, and expiration enforcement."""
    token = create_access_token(
        subject="farmer-user-123",
        claims={"phone_number": "+919876500000", "device_id": "DEV-TEST-001"},
        expires_delta=timedelta(minutes=15),
    )
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "farmer-user-123"
    assert payload["phone_number"] == "+919876500000"
    assert payload["device_id"] == "DEV-TEST-001"
    assert "exp" in payload

    # Test expired token
    expired_token = create_access_token(
        subject="expired-user",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(UnauthorizedAccessError) as exc_info:
        decode_access_token(expired_token)
    assert "expired" in str(exc_info.value).lower()

    # Test corrupted token
    with pytest.raises(UnauthorizedAccessError):
        decode_access_token("this.is.an.invalid.token")


def test_user_registration_and_duplicate_handling(client):
    """Verify farmer registration and duplicate phone number rejection with RFC 7807."""
    payload = {
        "phone_number": "+919111222333",
        "full_name": "Kishan Rao",
        "pin": "1234",
        "preferred_language": "mr",
        "kisan_id": "PMK-990011",
        "device_id": "DEV-HW-REG-001",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["user"]["full_name"] == "Kishan Rao"
    assert data["user"]["phone_number"] == "+919111222333"
    assert data["user"]["preferred_language"] == "mr"
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "DEV-HW-REG-001"
    assert data["token"]["access_token"] is not None
    assert data["token"]["token_type"] == "bearer"

    # Attempt registering same phone number again
    dup_resp = client.post("/api/v1/auth/register", json=payload)
    assert dup_resp.status_code == 422
    err_data = dup_resp.json()
    assert err_data["type"] == "urn:agrinova:error:validation-error"
    assert "already registered" in err_data["detail"]


def test_farmer_login_with_pin(client):
    """Verify PIN login flow with valid credentials, incorrect PIN, and unknown phone."""
    reg_payload = {
        "phone_number": "+919222333444",
        "full_name": "Savitri Devi",
        "pin": "7890",
        "preferred_language": "hi",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201

    # Successful login
    login_payload = {
        "phone_number": "+919222333444",
        "pin": "7890",
        "device_id": "DEV-SAVITRI-001",
    }
    login_resp = client.post("/api/v1/auth/login-pin", json=login_payload)
    assert login_resp.status_code == 200, login_resp.text
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Wrong PIN
    bad_pin_payload = {"phone_number": "+919222333444", "pin": "0000"}
    bad_resp = client.post("/api/v1/auth/login-pin", json=bad_pin_payload)
    assert bad_resp.status_code == 401
    assert "Invalid phone number or PIN" in bad_resp.json()["detail"]

    # Unknown user
    unknown_payload = {"phone_number": "+919999999999", "pin": "7890"}
    unknown_resp = client.post("/api/v1/auth/login-pin", json=unknown_payload)
    assert unknown_resp.status_code == 401


def test_device_session_establishment(client):
    """Verify hardware device registration and update."""
    dev_payload = {
        "device_id": "DEV-HARDWARE-PBP-555",
        "device_model": "Redmi Note 12",
        "os_version": "Android 14",
        "app_version": "1.2.0",
        "farmer_name": "Sunil Kumar",
        "preferred_language": "hi",
    }
    resp = client.post("/api/v1/auth/device-session", json=dev_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["device_id"] == "DEV-HARDWARE-PBP-555"
    assert data["device_model"] == "Redmi Note 12"
    assert data["is_active"] is True

    # Update app version
    dev_payload["app_version"] = "1.3.0"
    update_resp = client.post("/api/v1/auth/device-session", json=dev_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["app_version"] == "1.3.0"


def test_get_current_profile_me(client):
    """Verify /auth/me under JWT authentication, device header fallback, and unauthenticated state."""
    # 1. Unauthenticated request -> 401
    unauth_resp = client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 2. Authenticated via JWT
    reg_payload = {
        "phone_number": "+919333444555",
        "full_name": "Anand Shinde",
        "pin": "5555",
        "preferred_language": "mr",
        "device_id": "DEV-ANAND-001",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["token"]["access_token"]

    auth_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_resp.status_code == 200, auth_resp.text
    data = auth_resp.json()
    assert data["auth_type"] == "jwt"
    assert data["user"]["full_name"] == "Anand Shinde"
    assert data["user"]["phone_number"] == "+919333444555"

    # 3. Fallback via X-Device-ID header
    dev_resp = client.get("/api/v1/auth/me", headers={"X-Device-ID": "DEV-ANAND-001"})
    assert dev_resp.status_code == 200
    assert dev_resp.json()["auth_type"] == "device"


def test_consent_lifecycle_and_status(client):
    """Verify DPDP consent granting, revoking, status map, and invalid purpose rejection."""
    reg_payload = {
        "phone_number": "+919444555666",
        "full_name": "Meera Patel",
        "pin": "6666",
        "preferred_language": "hi",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initial status check -> all false
    status_resp = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["purposes"]["IRRIGATION_ADVISORY"] is False
    assert status_data["purposes"]["WEATHER_ALERTS"] is False

    # Grant IRRIGATION_ADVISORY consent
    grant_resp = client.post(
        "/api/v1/consent/grant",
        json={"purpose": "IRRIGATION_ADVISORY"},
        headers=headers,
    )
    assert grant_resp.status_code == 200
    assert grant_resp.json()["status"] == "GRANTED"

    # Status check -> IRRIGATION_ADVISORY is True
    status_resp2 = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp2.json()["purposes"]["IRRIGATION_ADVISORY"] is True
    assert status_resp2.json()["purposes"]["WEATHER_ALERTS"] is False

    # Revoke consent
    revoke_resp = client.post(
        "/api/v1/consent/revoke",
        json={"purpose": "IRRIGATION_ADVISORY"},
        headers=headers,
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "REVOKED"

    # Status check -> IRRIGATION_ADVISORY is False again
    status_resp3 = client.get("/api/v1/consent/status", headers=headers)
    assert status_resp3.json()["purposes"]["IRRIGATION_ADVISORY"] is False

    # Reject invalid purpose with 422
    invalid_resp = client.post(
        "/api/v1/consent/grant",
        json={"purpose": "UNKNOWN_UNAPPROVED_PURPOSE"},
        headers=headers,
    )
    assert invalid_resp.status_code == 422


def test_audit_logs_contain_security_events(client):
    """Verify security, registration, and consent events append to the immutable audit trail."""
    reg_payload = {
        "phone_number": "+919555666777",
        "full_name": "Gopal Sharma",
        "pin": "7777",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform consent actions
    client.post("/api/v1/consent/grant", json={"purpose": "WEATHER_ALERTS"}, headers=headers)
    client.post("/api/v1/consent/revoke", json={"purpose": "WEATHER_ALERTS"}, headers=headers)

    # Fetch audit logs
    logs_resp = client.get("/api/v1/consent/audit-logs", headers=headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) >= 3

    actions = [log["action"] for log in logs]
    assert "CONSENT_REVOKED" in actions
    assert "CONSENT_GRANTED" in actions
    assert "USER_REGISTERED" in actions
