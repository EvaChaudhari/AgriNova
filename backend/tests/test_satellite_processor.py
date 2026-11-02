"""Unit Tests for Satellite Multispectral Zonal Statistics Engine (Milestone C)."""

from datetime import date
import numpy as np

from app.engines.satellite_processor import SatelliteProcessor, SatelliteZonalResult


def test_zonal_stats_clear_sky():
    """Verify NDVI, NDWI, and NDMI calculations on a clear sky (<30% cloud) raster scene."""
    red, nir, green, swir, scl = SatelliteProcessor.simulate_multispectral_scene(
        crop_name="Cotton",
        das=60,
        cloud_pct=5.0,
        grid_size=(10, 10),
    )

    result = SatelliteProcessor.compute_zonal_statistics(
        red_band=red,
        nir_band=nir,
        green_band=green,
        swir_band=swir,
        scl_band=scl,
        acquisition_date=date(2026, 8, 15),
        sowing_date=date(2026, 6, 16),  # 60 DAS
        crop_name="Cotton",
    )

    assert isinstance(result, SatelliteZonalResult)
    assert result.status == "MEASURED"
    assert result.provenance_type == "DERIVED"
    assert result.cloud_cover_percent <= 10.0
    assert result.pixel_validity_count >= 90
    assert 0.20 <= result.mean_ndvi <= 0.90
    assert -0.80 <= result.mean_ndwi <= 0.80
    assert result.min_ndvi <= result.mean_ndvi <= result.max_ndvi
    assert result.quality_score >= 0.80


def test_zonal_stats_cloud_occlusion_fallback():
    """Verify that when cloud cover exceeds 30%, engine falls back to synthetic curve cleanly."""
    red, nir, green, swir, scl = SatelliteProcessor.simulate_multispectral_scene(
        crop_name="Cotton",
        das=60,
        cloud_pct=45.0,  # > 30% threshold
        grid_size=(10, 10),
    )

    result = SatelliteProcessor.compute_zonal_statistics(
        red_band=red,
        nir_band=nir,
        green_band=green,
        swir_band=swir,
        scl_band=scl,
        acquisition_date=date(2026, 8, 15),
        sowing_date=date(2026, 6, 16),  # 60 DAS
        crop_name="Cotton",
    )

    assert result.status == "CLOUD_OCCLUDED"
    assert result.source == "SYNTHETIC_PHENOLOGY_MODEL"
    assert result.provenance_type == "SYNTHETIC_FALLBACK"
    assert result.cloud_cover_percent >= 40.0
    assert result.quality_score == 0.60
    # Synthetic value must still be agronomically plausible for 60 DAS
    assert 0.40 <= result.mean_ndvi <= 0.85


def test_empty_array_pure_synthetic_fallback():
    """Verify empty/zero-size raster fallback."""
    empty = np.array([], dtype=np.uint16)
    result = SatelliteProcessor.compute_zonal_statistics(
        red_band=empty,
        nir_band=empty,
        green_band=empty,
        crop_name="Paddy",
    )
    assert result.status == "SYNTHETIC_FALLBACK"
    assert result.source == "SYNTHETIC_PHENOLOGY_MODEL"
    assert result.provenance_type == "SYNTHETIC_FALLBACK"
    assert -1.0 <= result.mean_ndvi <= 1.0


def test_scl_masking_excludes_cloud_shadows_and_cirrus():
    """Verify that cloudy pixels marked in SCL do not corrupt valid vegetation mean values."""
    # 2x2 grid: 2 clear vegetation pixels, 2 cloud pixels
    red = np.array([[1000, 1000], [8000, 8000]], dtype=np.uint16)
    nir = np.array([[4000, 4000], [8500, 8500]], dtype=np.uint16)
    green = np.array([[1200, 1200], [8000, 8000]], dtype=np.uint16)
    scl = np.array(
        [[SatelliteProcessor.SCL_VEGETATION, SatelliteProcessor.SCL_VEGETATION],
         [SatelliteProcessor.SCL_CLOUD_HIGH_PROB, SatelliteProcessor.SCL_CLOUD_SHADOW]],
        dtype=np.uint8,
    )

    result = SatelliteProcessor.compute_zonal_statistics(
        red_band=red,
        nir_band=nir,
        green_band=green,
        scl_band=scl,
        crop_name="Cotton",
    )

    # 50% cloud cover -> triggers CLOUD_OCCLUDED fallback
    assert result.status == "CLOUD_OCCLUDED"
    assert result.cloud_cover_percent == 50.0
