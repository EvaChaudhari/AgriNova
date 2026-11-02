"""Unit and Integration Tests for Security Hardening, Rate Limiting & Revocation (Milestone F)."""

import pytest
from app.core.rate_limiter import (
    blacklist_token,
    clear_token_blacklist,
    global_rate_limiter,
    is_token_blacklisted,
)
from app.core.security import create_access_token


@pytest.fixture(autouse=True)
def cleanup_security_state():
    """Reset rate limiter and blacklist before and after tests."""
    global_rate_limiter.reset()
    clear_token_blacklist()
    yield
    global_rate_limiter.reset()
    clear_token_blacklist()


def test_owasp_security_headers_injected(client):
    """Verify OWASP recommended security headers are injected into HTTP responses."""
    resp = client.get("/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age" in headers.get("Strict-Transport-Security", "")
    assert headers.get("Content-Security-Policy") == "default-src 'self'"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_sliding_window_rate_limiter_logic():
    """Verify sliding-window rate limiter trips when threshold is reached and reports Retry-After."""
    key = "test-client-ip:test-path"
    max_reqs = 5
    window_sec = 60

    # First 5 calls pass
    for _ in range(max_reqs):
        is_limited, retry_after = global_rate_limiter.is_rate_limited(key, max_reqs, window_sec)
        assert is_limited is False
        assert retry_after == 0

    # 6th call must be rate limited
    is_limited, retry_after = global_rate_limiter.is_rate_limited(key, max_reqs, window_sec)
    assert is_limited is True
    assert 0 < retry_after <= window_sec


def test_jwt_token_blacklisting():
    """Verify token revocation blacklist rejects revoked tokens."""
    token = create_access_token(subject="user_123")
    assert is_token_blacklisted(token) is False

    # Revoke token
    blacklist_token(token)
    assert is_token_blacklisted(token) is True
    assert is_token_blacklisted(f"Bearer {token}") is True


def test_logout_endpoint_and_revocation(client):
    """Verify POST /api/v1/auth/logout revokes JWT token preventing subsequent requests."""
    # Register and login user
    reg_payload = {
        "phone_number": "+919999000099",
        "full_name": "Ramesh Kumar",
        "pin": "1234",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_resp = client.post(
        "/api/v1/auth/login-pin",
        json={"phone_number": "+919999000099", "pin": "1234"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Verify /me succeeds before logout
    me_resp1 = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_resp1.status_code == 200

    # Call /logout
    logout_resp = client.post("/api/v1/auth/logout", headers=auth_header)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "success"

    # Subsequent /me with same token must fail with 401 Unauthorized
    me_resp2 = client.get("/api/v1/auth/me", headers=auth_header)
    assert me_resp2.status_code == 401
    body = me_resp2.json()
    assert "revoked" in body["detail"].lower()

