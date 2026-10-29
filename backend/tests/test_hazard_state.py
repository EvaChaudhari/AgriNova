"""Unit Tests for Extreme Weather Hazard State Machine."""

import pytest
from app.engines.hazard_state import HazardStateMachine, HazardEngineInput


def test_storm_flood_mode_transition_and_restrictions():
    """Verify state machine triggers STORM_FLOOD_MODE when 24h rainfall >= 50 mm and halts chemicals."""
    inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=55.0,
        groundwater_depth_mbgl=12.0,
        rainfall_deficit_percent=10.0,
        dem_slope_percent=2.0,
    )
    result = HazardStateMachine.evaluate(inputs)

    assert result.current_state == "STORM_FLOOD_MODE"
    assert "HALT_ALL_CHEMICAL_SPRAYING" in result.enforced_restrictions
    assert "HALT_FERTILIZERS" in result.enforced_restrictions
    assert "CLEAR_DRAINAGE_FURROWS" in result.enforced_restrictions
    # Check that any spraying is categorically prohibited
    assert any("pesticide" in d.lower() for d in result.actionable_directives)


def test_storm_flood_mode_slope_analysis():
    """Verify DEM slope analysis correctly distinguishes erosion vs root asphyxiation risk."""
    # Steep slope (> 3%)
    steep_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=50.0,
        groundwater_depth_mbgl=12.0,
        rainfall_deficit_percent=5.0,
        dem_slope_percent=4.5,
    )
    steep_res = HazardStateMachine.evaluate(steep_inputs)
    assert steep_res.slope_risk == "HIGH_TOPSOIL_EROSION_RISK"
    assert "contour bunds" in steep_res.actionable_directives[3].lower()

    # Low flat slope (<= 3%)
    flat_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=50.0,
        groundwater_depth_mbgl=12.0,
        rainfall_deficit_percent=5.0,
        dem_slope_percent=1.2,
    )
    flat_res = HazardStateMachine.evaluate(flat_inputs)
    assert flat_res.slope_risk == "ROOT_ASPHYXIATION_RISK"
    assert "stagnant water" in flat_res.actionable_directives[3].lower()


def test_el_nino_drought_mode_transition():
    """Verify transition to EL_NINO_DROUGHT_MODE when groundwater > 18 mbgl and deficit > 35%."""
    drought_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=0.0,
        groundwater_depth_mbgl=19.5,  # > 18.0 mbgl
        rainfall_deficit_percent=42.0,  # > 35.0%
        dem_slope_percent=1.5,
        ndwi=-0.10,
    )
    result = HazardStateMachine.evaluate(drought_inputs)

    assert result.current_state == "EL_NINO_DROUGHT_MODE"
    assert "FORBID_SURFACE_FLOOD_IRRIGATION" in result.enforced_restrictions
    assert result.is_critical_water_stress is False
    assert any("mulch" in d.lower() for d in result.actionable_directives)
    assert any("night" in d.lower() for d in result.actionable_directives)


def test_critical_water_stress_submode():
    """Verify sub-mode CRITICAL_WATER_STRESS triggers when NDWI < -0.20 during drought."""
    crit_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=0.0,
        groundwater_depth_mbgl=21.0,
        rainfall_deficit_percent=50.0,
        dem_slope_percent=1.5,
        ndwi=-0.25,  # < -0.20
    )
    result = HazardStateMachine.evaluate(crit_inputs)

    assert result.current_state == "EL_NINO_DROUGHT_MODE"
    assert result.is_critical_water_stress is True
    assert "ENFORCE_DEFICIT_IRRIGATION_ONLY" in result.enforced_restrictions
    assert any("kaolin" in d.lower() for d in result.actionable_directives)


def test_normal_operating_envelope():
    """Verify normal envelope when all parameters are stable."""
    normal_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=10.0,
        groundwater_depth_mbgl=12.0,
        rainfall_deficit_percent=10.0,
        dem_slope_percent=1.5,
        ndwi=0.15,
    )
    result = HazardStateMachine.evaluate(normal_inputs)

    assert result.current_state == "NORMAL_MODE"
    assert len(result.enforced_restrictions) == 0
    assert result.is_critical_water_stress is False

