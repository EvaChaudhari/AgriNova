"""Unit Tests for FAO-56 Penman-Monteith and Soil Water Balance Engine."""

import pytest
from app.engines.fao56_hydrology import (
    calculate_fao56_et0,
    FAO56DailyET0Input,
    calculate_water_balance,
    WaterBalanceInput,
    calculate_effective_rainfall,
    calculate_capillary_rise,
)


def test_fao56_et0_standard_benchmark():
    """Verify FAO-56 Penman-Monteith ET0 calculation against standard semi-arid climatic benchmark."""
    # FAO-56 representative semi-arid summer scenario (Lat 17.5°N, elevation 250m, mid-summer Julian day 180)
    params = FAO56DailyET0Input(
        t_min=22.0,
        t_max=36.0,
        rh_mean=50.0,
        wind_speed_2m=2.2,
        solar_radiation_mj_m2=22.5,
        elevation_m=250.0,
        latitude_deg=17.5,
        day_of_year=180,
    )
    et0 = calculate_fao56_et0(params)

    # Standard FAO-56 benchmark range for warm summer: 5.5 to 7.0 mm/day
    assert 5.0 <= et0 <= 7.5, f"Expected ET0 in [5.0, 7.5], got {et0}"
    assert et0 == round(et0, 2)


def test_fao56_et0_temperature_and_radiation_response():
    """Verify ET0 scales logically with solar radiation and temperature."""
    cool_winter_params = FAO56DailyET0Input(
        t_min=12.0,
        t_max=24.0,
        rh_mean=60.0,
        wind_speed_2m=1.2,
        solar_radiation_mj_m2=15.0,
        elevation_m=250.0,
        latitude_deg=17.5,
        day_of_year=15,  # January
    )
    et0_winter = calculate_fao56_et0(cool_winter_params)

    hot_summer_params = FAO56DailyET0Input(
        t_min=26.0,
        t_max=42.0,
        rh_mean=40.0,
        wind_speed_2m=3.0,
        solar_radiation_mj_m2=25.0,
        elevation_m=250.0,
        latitude_deg=17.5,
        day_of_year=135,  # May
    )
    et0_summer = calculate_fao56_et0(hot_summer_params)

    assert et0_summer > et0_winter, f"Summer ET0 ({et0_summer}) must exceed Winter ET0 ({et0_winter})"
    assert et0_winter >= 2.5
    assert et0_summer >= 6.5


def test_effective_rainfall_depletion():
    """Verify USDA-SCS effective rainfall deductions."""
    assert calculate_effective_rainfall(3.0) == 0.0  # Light rain (<5mm) evaporates
    assert calculate_effective_rainfall(25.0) == 16.0  # 0.8 * (25 - 5) = 16 mm
    assert calculate_effective_rainfall(70.0) == 42.0  # Heavy runoff reduction


def test_capillary_rise():
    """Verify capillary rise occurs only for shallow groundwater."""
    assert calculate_capillary_rise(15.0, "Vertisol") == 0.0
    assert calculate_capillary_rise(1.5, "Vertisol") == 0.8
    assert calculate_capillary_rise(0.8, "Vertisol") == 1.8


def test_water_balance_trigger_irrigate():
    """Verify trigger transitions to IRRIGATE when root zone depletion exceeds RAW."""
    # Cotton in Flowering stage on Vertisol:
    # theta_fc = 0.40, theta_wp = 0.22 -> diff = 0.18
    # root_depth = 1.2m -> TAW = 216 mm
    # p = 0.65 -> RAW approx 130-140 mm
    inputs = WaterBalanceInput(
        crop_name="Cotton",
        growth_stage="FLOWERING",
        soil_texture="Vertisol",
        et0_mm_day=6.0,
        rainfall_24h_mm=0.0,
        previous_depletion_mm=135.0,  # Near RAW limit
        groundwater_depth_mbgl=14.0,
        irrigation_method="DRIP",
    )
    res = calculate_water_balance(inputs)

    assert res.kc == 1.20
    assert res.etc_mm == 7.20
    assert res.trigger == "IRRIGATE"
    assert res.recommended_depth_mm > 0.0
    # Drip efficiency is 0.90
    assert res.recommended_depth_mm >= round(res.root_zone_depletion_mm / 0.90, 1) - 0.2


def test_water_balance_trigger_hold():
    """Verify trigger stays at HOLD when soil depletion is safely within buffering capacity."""
    inputs = WaterBalanceInput(
        crop_name="Cotton",
        growth_stage="FLOWERING",
        soil_texture="Vertisol",
        et0_mm_day=5.0,
        rainfall_24h_mm=0.0,
        previous_depletion_mm=20.0,  # Plenty of moisture left
        groundwater_depth_mbgl=14.0,
        irrigation_method="DRIP",
    )
    res = calculate_water_balance(inputs)

    assert res.trigger == "HOLD"
    assert res.recommended_depth_mm == 0.0


def test_water_balance_trigger_drain():
    """Verify trigger transitions to DRAIN during heavy storm rainfall on clay soil."""
    inputs = WaterBalanceInput(
        crop_name="Cotton",
        growth_stage="VEGETATIVE",
        soil_texture="Vertisol",
        et0_mm_day=3.0,
        rainfall_24h_mm=65.0,  # Intense rainfall event
        previous_depletion_mm=10.0,
        groundwater_depth_mbgl=8.0,
        irrigation_method="DRIP",
    )
    res = calculate_water_balance(inputs)

    assert res.trigger == "DRAIN"
    assert res.recommended_depth_mm == 0.0
    assert "Drain excess furrow water" in res.details

