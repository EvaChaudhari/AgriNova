"""Unit and Integration Tests for Unified Chat Receptor Endpoint."""

import pytest
from app.models.chat import ChatSession, ChatMessage


def test_chat_receptor_new_session_instantiation(client, seed_test_farmer, db_session):
    """Verify receptor creates a new session when session_id is None, empty, or 'new'."""
    payload = {
        "device_id": "TEST-HARDWARE-UUID-001",
        "session_id": "new",
        "query_text": "मेरी कपास की फसल के लिए आज क्या सलाह है?",
        "language": "hi",
    }
    response = client.post("/api/v1/chat/receptor", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["session_id"] != ""
    assert data["session_id"] != "new"
    assert "reply_text" in data
    assert len(data["reply_text"]) > 10
    assert data["audio_base64_url"] is not None
    assert data["audio_base64_url"].startswith("data:audio/wav;base64,")
    assert "injected_context" in data
    assert data["injected_context"]["crop_name"] == "Cotton"
    assert data["injected_context"]["device_id"] == "TEST-HARDWARE-UUID-001"

    # Verify session persisted in database
    session_record = db_session.query(ChatSession).filter(ChatSession.id == data["session_id"]).first()
    assert session_record is not None
    assert session_record.device_id == "TEST-HARDWARE-UUID-001"

    messages = db_session.query(ChatMessage).filter(ChatMessage.session_id == data["session_id"]).all()
    assert len(messages) == 1
    assert messages[0].query_text == payload["query_text"]


def test_chat_receptor_existing_session_history_appending(client, seed_test_farmer, db_session):
    """Verify receptor appends subsequent turns to existing session history."""
    # Turn 1: Create session
    payload_1 = {
        "device_id": "TEST-HARDWARE-UUID-001",
        "session_id": "new",
        "query_text": "फसल में सिंचाई कब करनी है?",
        "language": "hi",
    }
    resp1 = client.post("/api/v1/chat/receptor", json=payload_1)
    assert resp1.status_code == 200
    session_id = resp1.json()["session_id"]

    # Turn 2: Follow-up question using the created session_id
    payload_2 = {
        "device_id": "TEST-HARDWARE-UUID-001",
        "session_id": session_id,
        "query_text": "क्या मुझे अभी खाद देनी चाहिए?",
        "language": "hi",
    }
    resp2 = client.post("/api/v1/chat/receptor", json=payload_2)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Session ID should match
    assert data2["session_id"] == session_id

    # Verify database holds both turns under the same session
    messages = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    assert len(messages) == 2
    assert messages[0].query_text == payload_1["query_text"]
    assert messages[1].query_text == payload_2["query_text"]


def test_chat_receptor_multipart_voice_and_vision_handling(client, seed_test_farmer):
    """Verify multipart form endpoint handles voice transcript and image inputs."""
    dummy_wav = b"RIFF" + b"\x00" * 40
    dummy_img = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header

    files = {
        "audio_file": ("test_voice.wav", dummy_wav, "audio/wav"),
        "image_file": ("leaf.jpg", dummy_img, "image/jpeg"),
    }
    data = {
        "device_id": "TEST-HARDWARE-UUID-001",
        "session_id": "new",
        "language": "hi",
    }
    response = client.post("/api/v1/chat/receptor", data=data, files=files)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["session_id"] is not None
    assert result["audio_base64_url"] is not None
    assert "reply_text" in result


def test_bootstrap_endpoint(client, seed_test_farmer):
    """Verify /api/v1/bootstrap resolves device state and runs scientific engines."""
    # Onboarded device
    resp = client.get("/api/v1/bootstrap?device_id=TEST-HARDWARE-UUID-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_onboarded"] is True
    assert data["profile"]["farmer_name"] == "Rameshwar Patil"
    assert data["context"] is not None
    assert "hydrology" in data["context"]
    assert "hazard" in data["context"]
    assert data["hazard_state"] in ("NORMAL_MODE", "STORM_FLOOD_MODE", "EL_NINO_DROUGHT_MODE")

    # Non-onboarded device
    resp_unknown = client.get("/api/v1/bootstrap?device_id=UNKNOWN-DEVICE-XYZ")
    assert resp_unknown.status_code == 200
    data_unknown = resp_unknown.json()
    assert data_unknown["is_onboarded"] is False
    assert data_unknown["profile"] is None


def test_chat_receptor_storm_flood_halt_spraying_override(client, seed_test_farmer, monkeypatch):
    """Verify that under STORM_FLOOD_MODE, chat receptor strictly refuses pesticide spraying."""
    from app.services import weather_service
    from app.services.weather_service import WeatherSnapshot

    # Monkeypatch weather service to simulate severe storm forecast (65 mm rain)
    async def mock_fetch_weather(lat, lon):
        return WeatherSnapshot(
            t_min=24.0,
            t_max=30.0,
            t_mean=27.0,
            rh_mean=90.0,
            wind_speed_2m=4.5,
            solar_radiation_mj_m2=12.0,
            rainfall_24h_mm=65.0,  # >= 50 mm threshold
            seasonal_deficit_percent=0.0,
            source="TEST_STORM_ALERT",
            condition_description="Heavy Monsoon Downpour",
            recorded_at="2026-10-29T00:00:00Z",
        )

    monkeypatch.setattr("app.services.context_builder.fetch_weather_data", mock_fetch_weather)

    payload = {
        "device_id": "TEST-HARDWARE-UUID-001",
        "session_id": "new",
        "query_text": "क्या मैं आज कीटनाशक का छिड़काव कर सकता हूँ?",
        "language": "hi",
    }
    response = client.post("/api/v1/chat/receptor", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["hazard_state"] == "STORM_FLOOD_MODE"
    assert "HALT_ALL_CHEMICAL_SPRAYING" in data["injected_context"]["hazard"]["enforced_restrictions"]
    reply = data["reply_text"]
    # Check that the reply strictly advises against spraying
    assert ("छिड़काव बिल्कुल न करें" in reply or "छिड़काव न करें" in reply or "रोकें" in reply or "halt" in reply.lower())
