"""Unit Tests for Agronomic Services (Vision, Speech, STAC, Weather)."""

import pytest
from datetime import date, timedelta
from app.services.vision_service import LeafVisionService
from app.services.weather_service import fetch_weather_data
from app.services.speech_service import SpeechService
from app.engines.satellite_stac import calculate_synthetic_indices, fetch_sentinel2_indices


@pytest.mark.asyncio
async def test_leaf_vision_validator():
    """Verify vision service leaf validator, CIB chemical safety guidelines, and IPM recommendations."""
    # Test valid leaf image
    dummy_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 200
    diag = await LeafVisionService.diagnose_leaf(dummy_jpeg, crop_hint="Cotton")

    assert diag.is_valid_leaf is True
    assert diag.crop_identified == "Cotton"
    assert "Pink Bollworm" in diag.condition
    assert diag.confidence > 0.80
    assert len(diag.ipm_recommendations) > 0
    assert any("pheromone" in ipm.lower() or "neem" in ipm.lower() for ipm in diag.ipm_recommendations)
    assert len(diag.cib_approved_chemicals) > 0
    # Must specify exact dilution dosage
    assert "g per 10 Litres" in diag.cib_approved_chemicals[0]["dosage"] or "ml per 10 Litres" in diag.cib_approved_chemicals[0]["dosage"]

    # Test invalid / empty byte payload
    invalid_diag = await LeafVisionService.diagnose_leaf(b"", crop_hint="Cotton")
    assert invalid_diag.is_valid_leaf is False
    assert invalid_diag.confidence == 0.0


@pytest.mark.asyncio
async def test_weather_fallback():
    """Verify weather service falls back to IMD agro-climatic normal when API key is not present."""
    weather = await fetch_weather_data(17.5, 78.5)
    assert weather.source in ("LIVE_API", "AGRO_CLIMATIC_FALLBACK")
    assert 10.0 <= weather.t_min <= 30.0
    assert 20.0 <= weather.t_max <= 45.0
    assert weather.t_mean == round((weather.t_min + weather.t_max) / 2.0, 1)
    assert 30.0 <= weather.rh_mean <= 95.0
    assert weather.solar_radiation_mj_m2 > 10.0


@pytest.mark.asyncio
async def test_synthetic_satellite_phenological_curve():
    """Verify synthetic phenology NDVI and NDWI curve progression over DAS."""
    sowing = date.today() - timedelta(days=10)  # Emergence stage
    ind_early = calculate_synthetic_indices("Cotton", sowing)
    assert 0.15 <= ind_early.ndvi <= 0.30
    assert ind_early.ndwi < 0.0  # Canopy water low

    sowing_peak = date.today() - timedelta(days=70)  # Peak flowering stage
    ind_peak = calculate_synthetic_indices("Cotton", sowing_peak)
    assert 0.70 <= ind_peak.ndvi <= 0.90
    assert ind_peak.ndwi > 0.10  # Full canopy hydration
    assert ind_peak.ndvi > ind_early.ndvi

    sowing_late = date.today() - timedelta(days=140)  # Senescence stage
    ind_late = calculate_synthetic_indices("Cotton", sowing_late)
    assert ind_late.ndvi < ind_peak.ndvi


@pytest.mark.asyncio
async def test_speech_pipeline():
    """Verify speech service transcription and audio synthesis fallback."""
    # STT
    dummy_wav = b"RIFF" + b"\x00" * 40
    hi_text = await SpeechService.transcribe_audio(dummy_wav, "hi")
    assert len(hi_text) > 0
    te_text = await SpeechService.transcribe_audio(dummy_wav, "te")
    assert len(te_text) > 0

    # TTS
    tts_url = await SpeechService.synthesize_speech("नमस्ते किसान भाई", "hi")
    assert tts_url.startswith("data:audio/wav;base64,")
    assert len(tts_url) > 100

