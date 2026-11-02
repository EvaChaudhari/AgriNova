"""Unit and Integration Tests for Farmer Notifications API (Milestone E)."""

from datetime import date
import pytest
from app.models.profile import DeviceProfile
from app.services.notification_service import NotificationService


@pytest.fixture
def notif_test_farmer(client, db_session):
    """Seed farmer profile for notifications."""
    device_id = "DEV-NOTIF-TEST-001"
    profile = DeviceProfile(
        device_id=device_id,
        farmer_name="Sunita Deshmukh",
        preferred_language="mr",
        phone_number="+919855009900",
        kisan_id="PMK-NOTIF-1122",
    )
    db_session.add(profile)
    db_session.commit()
    return {"device_id": device_id}


def test_notification_creation_and_localization(db_session, notif_test_farmer):
    """Verify localized alert generation in Hindi, Marathi, Telugu, and English."""
    device_id = notif_test_farmer["device_id"]

    # 1. Marathi Weather Hazard
    mr_alert = NotificationService.create_hazard_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        rainfall_mm=60.0,
        language="mr",
    )
    assert mr_alert.language == "mr"
    assert "धोका इशारा" in mr_alert.title
    assert "पावसाची" in mr_alert.body
    assert mr_alert.priority == "HIGH"

    # 2. Hindi Weather Hazard (Urgent >= 75mm)
    hi_alert = NotificationService.create_hazard_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        rainfall_mm=85.0,
        language="hi",
    )
    assert hi_alert.language == "hi"
    assert "चेतावनी" in hi_alert.title
    assert hi_alert.priority == "URGENT"

    # 3. Telugu Irrigation Alert
    te_alert = NotificationService.create_irrigation_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        language="te",
    )
    assert te_alert.language == "te"
    assert "నీటిపారుదల" in te_alert.title

    # 4. English Checkpoint Reminder
    en_alert = NotificationService.create_checkpoint_reminder(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        checkpoint_title="Basal Fertilizer",
        target_date=date.today(),
        language="en",
    )
    assert en_alert.language == "en"
    assert "Basal Fertilizer" in en_alert.title
    assert en_alert.priority == "ROUTINE"


def test_get_notifications_api(client, db_session, notif_test_farmer):
    """Verify GET /api/v1/notifications retrieves unread and all notifications."""
    device_id = notif_test_farmer["device_id"]

    # Seed 2 notifications
    NotificationService.create_hazard_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        rainfall_mm=55.0,
        language="hi",
    )
    NotificationService.create_irrigation_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        language="hi",
    )

    resp = client.get(f"/api/v1/notifications?device_id={device_id}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert items[0]["is_read"] is False

    # Filter unread
    resp_unread = client.get(f"/api/v1/notifications?device_id={device_id}&unread_only=true")
    assert resp_unread.status_code == 200
    assert len(resp_unread.json()) == 2


def test_acknowledge_notification_api(client, db_session, notif_test_farmer):
    """Verify POST /api/v1/notifications/{id}/read acknowledges notification."""
    device_id = notif_test_farmer["device_id"]

    alert = NotificationService.create_hazard_alert(
        db=db_session,
        device_id=device_id,
        plot_id=None,
        rainfall_mm=70.0,
        language="en",
    )

    resp = client.post(f"/api/v1/notifications/{alert.id}/read?device_id={device_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == alert.id
    assert data["is_read"] is True
    assert data["acknowledged_at"] is not None

    # Verify unread query now returns 0
    resp_unread = client.get(f"/api/v1/notifications?device_id={device_id}&unread_only=true")
    assert resp_unread.status_code == 200
    assert len(resp_unread.json()) == 0


def test_acknowledge_notification_not_found(client):
    """Verify 404 EntityNotFoundError for nonexistent notification."""
    resp = client.post("/api/v1/notifications/99999/read")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:agrinova:error:not-found"
