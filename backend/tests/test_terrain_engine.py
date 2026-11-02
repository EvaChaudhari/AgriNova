"""Unit Tests for Geospatial Terrain & Topography Engine (Milestone C)."""

import math
from app.engines.terrain_engine import TerrainEngine, TerrainAnalysisResult


def test_slope_degrees_conversion():
    """Verify trigonometric conversion of slope percentage to degrees."""
    assert TerrainEngine.calculate_slope_degrees(0.0) == 0.0
    assert TerrainEngine.calculate_slope_degrees(100.0) == 45.0
    assert 0.85 <= TerrainEngine.calculate_slope_degrees(1.5) <= 0.87
    assert 1.70 <= TerrainEngine.calculate_slope_degrees(3.0) <= 1.73


def test_erosion_hazard_classification():
    """Verify erosion hazard rules based on slope thresholds."""
    # Steep slope (> 3.0%) -> HIGH_EROSION_RISK
    hazard, directive = TerrainEngine.classify_erosion_hazard(3.5)
    assert hazard == "HIGH_EROSION_RISK"
    assert "contour bunds" in directive.lower()

    # Flat slope (<= 1.0%) -> WATERLOGGING_SUSCEPTIBLE
    hazard, directive = TerrainEngine.classify_erosion_hazard(0.8)
    assert hazard == "WATERLOGGING_SUSCEPTIBLE"
    assert "drainage furrows" in directive.lower()

    # Moderate slope (1.0% - 3.0%) -> STABLE
    hazard, directive = TerrainEngine.classify_erosion_hazard(1.8)
    assert hazard == "STABLE"
    assert "optimal" in directive.lower()


def test_topographic_wetness_index():
    """Verify TWI behavior: flat terrains have higher wetness potential than steep slopes."""
    flat_twi = TerrainEngine.calculate_topographic_wetness_index(0.5)
    moderate_twi = TerrainEngine.calculate_topographic_wetness_index(2.0)
    steep_twi = TerrainEngine.calculate_topographic_wetness_index(8.0)

    assert flat_twi > moderate_twi > steep_twi
    assert flat_twi > 12.0  # High moisture accumulation
    assert steep_twi < 10.0   # Fast runoff / shedding


def test_regional_elevation_hypsometric_fallbacks():
    """Verify regional elevation baselines across Indian agro-ecological zones."""
    # Hyderabad / Deccan Plateau
    deccan = TerrainEngine.estimate_regional_elevation_m(lat=17.38, lon=78.48)
    assert deccan == 540.0

    # Kanpur / Indo-Gangetic Alluvial Plain
    gangetic = TerrainEngine.estimate_regional_elevation_m(lat=26.45, lon=80.33)
    assert gangetic == 175.0

    # Coastal Ratnagiri
    coastal = TerrainEngine.estimate_regional_elevation_m(lat=16.99, lon=73.30)
    assert coastal == 35.0


def test_analyze_plot_terrain_full_pipeline():
    """Verify end-to-end terrain analysis with both measured values and fallback derivations."""
    # Case 1: Known surveyor measurements
    result_known = TerrainEngine.analyze_plot_terrain(
        centroid_lat=17.50,
        centroid_lon=78.50,
        known_elevation_m=265.0,
        known_slope_percent=4.2,
    )
    assert isinstance(result_known, TerrainAnalysisResult)
    assert result_known.elevation_m == 265.0
    assert result_known.slope_percent == 4.2
    assert result_known.erosion_hazard == "HIGH_EROSION_RISK"
    assert result_known.source == "COPERNICUS_DEM_SURVEY"
    assert result_known.provenance_type == "MEASURED"

    # Case 2: Pure coordinate fallback
    result_fallback = TerrainEngine.analyze_plot_terrain(
        centroid_lat=17.50,
        centroid_lon=78.50,
        known_elevation_m=None,
        known_slope_percent=None,
    )
    assert result_fallback.elevation_m == 540.0
    assert result_fallback.provenance_type == "SYNTHETIC_FALLBACK"
    assert result_fallback.source == "HYPSOMETRIC_FALLBACK"
    assert result_fallback.twi > 0.0
