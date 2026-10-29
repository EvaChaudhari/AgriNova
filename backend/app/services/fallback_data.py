"""Deterministic Regional Fallback Baselines.

Calibrated to Indian agro-ecological zones, ICAR benchmarks, CGWB district water tables,
and FAO-56 standard crop coefficient tables.
"""

from typing import Any


# CGWB (Central Ground Water Board) district groundwater seasonal medians (in mbgl)
CGWB_DISTRICT_GROUNDWATER_MBGL: dict[str, float] = {
    # Telangana
    "warangal": 11.2,
    "adilabad": 9.8,
    "nalgonda": 14.5,
    "khammam": 8.4,
    "karimnagar": 12.1,
    "hyderabad": 16.8,
    "mahabubnagar": 19.4,  # Over-exploited
    # Maharashtra (Vidarbha / Marathwada)
    "akola": 12.6,
    "wardha": 10.5,
    "ahmednagar": 18.9,  # Severe deficit
    "yavatmal": 13.2,
    "nagpur": 9.2,
    "amravati": 14.1,
    "solapur": 20.2,  # Drought-prone
    # Andhra Pradesh
    "anantapur": 22.4,  # Severe drought zone
    "guntur": 7.5,
    "kurnool": 16.3,
    # Karnataka
    "belagavi": 10.8,
    "raichur": 17.6,
    "kalaburagi": 15.2,
    # North India
    "karnal": 16.5,
    "ludhiana": 21.0,
    "indore": 14.8,
    "ujjain": 15.3,
}

DEFAULT_GROUNDWATER_DEPTH_MBGL = 12.5


# IMD (India Meteorological Department) Agro-Climatic Normals (Monthly baseline estimates)
IMD_AGROCLIMATIC_NORMALS: dict[int, dict[str, float]] = {
    1: {"t_min": 14.0, "t_max": 28.5, "rh": 60.0, "wind_speed": 1.5, "radiation": 16.5, "rain_24h": 0.2, "deficit_pct": 5.0},
    2: {"t_min": 16.5, "t_max": 31.0, "rh": 52.0, "wind_speed": 1.8, "radiation": 18.2, "rain_24h": 0.4, "deficit_pct": 5.0},
    3: {"t_min": 20.0, "t_max": 35.5, "rh": 45.0, "wind_speed": 2.2, "radiation": 21.0, "rain_24h": 0.5, "deficit_pct": 10.0},
    4: {"t_min": 24.5, "t_max": 39.5, "rh": 40.0, "wind_speed": 2.5, "radiation": 23.5, "rain_24h": 1.2, "deficit_pct": 15.0},
    5: {"t_min": 27.0, "t_max": 42.0, "rh": 42.0, "wind_speed": 2.8, "radiation": 24.2, "rain_24h": 3.5, "deficit_pct": 20.0},
    6: {"t_min": 25.5, "t_max": 36.0, "rh": 70.0, "wind_speed": 3.4, "radiation": 18.5, "rain_24h": 8.5, "deficit_pct": 10.0},
    7: {"t_min": 24.0, "t_max": 31.5, "rh": 82.0, "wind_speed": 3.2, "radiation": 15.0, "rain_24h": 14.2, "deficit_pct": 0.0},
    8: {"t_min": 23.5, "t_max": 30.5, "rh": 84.0, "wind_speed": 2.9, "radiation": 14.5, "rain_24h": 12.8, "deficit_pct": 0.0},
    9: {"t_min": 23.0, "t_max": 31.5, "rh": 78.0, "wind_speed": 2.1, "radiation": 17.0, "rain_24h": 7.5, "deficit_pct": 5.0},
    10: {"t_min": 20.5, "t_max": 32.0, "rh": 65.0, "wind_speed": 1.6, "radiation": 18.5, "rain_24h": 3.2, "deficit_pct": 10.0},
    11: {"t_min": 17.0, "t_max": 29.5, "rh": 62.0, "wind_speed": 1.4, "radiation": 17.0, "rain_24h": 1.1, "deficit_pct": 8.0},
    12: {"t_min": 14.5, "t_max": 28.0, "rh": 60.0, "wind_speed": 1.3, "radiation": 16.0, "rain_24h": 0.3, "deficit_pct": 5.0},
}


# Regional Soil Type Benchmarks (Soil Health Card Calibration)
SOIL_TYPE_BENCHMARKS: dict[str, dict[str, Any]] = {
    "Vertisol": {
        "description": "Deep Black Cotton Soil (Deccan Trap)",
        "ph": 7.8,
        "nitrogen_kg_ha": 140.0,  # Low
        "phosphorus_kg_ha": 18.0,  # Medium
        "potassium_kg_ha": 280.0,  # High
        "organic_carbon_percent": 0.45,  # Low-medium
        "field_capacity": 0.40,  # m3/m3 (40% volumetric water content)
        "wilting_point": 0.22,  # m3/m3 (22%)
        "drainage_rate_mm_day": 12.0,
    },
    "Alfisol": {
        "description": "Red Sandy/Loamy Soil",
        "ph": 6.2,
        "nitrogen_kg_ha": 160.0,
        "phosphorus_kg_ha": 14.0,
        "potassium_kg_ha": 180.0,
        "organic_carbon_percent": 0.35,
        "field_capacity": 0.24,
        "wilting_point": 0.12,
        "drainage_rate_mm_day": 35.0,
    },
    "Inceptisol": {
        "description": "Alluvial / Loamy Plains",
        "ph": 7.2,
        "nitrogen_kg_ha": 210.0,
        "phosphorus_kg_ha": 22.0,
        "potassium_kg_ha": 220.0,
        "organic_carbon_percent": 0.55,
        "field_capacity": 0.32,
        "wilting_point": 0.16,
        "drainage_rate_mm_day": 25.0,
    },
    "Sandy Loam": {
        "description": "Light coarse soil with rapid drainage",
        "ph": 6.8,
        "nitrogen_kg_ha": 120.0,
        "phosphorus_kg_ha": 12.0,
        "potassium_kg_ha": 150.0,
        "organic_carbon_percent": 0.28,
        "field_capacity": 0.18,
        "wilting_point": 0.08,
        "drainage_rate_mm_day": 55.0,
    },
    "Clay Loam": {
        "description": "Balanced agricultural loam",
        "ph": 7.5,
        "nitrogen_kg_ha": 175.0,
        "phosphorus_kg_ha": 20.0,
        "potassium_kg_ha": 240.0,
        "organic_carbon_percent": 0.50,
        "field_capacity": 0.35,
        "wilting_point": 0.18,
        "drainage_rate_mm_day": 20.0,
    },
}


# FAO-56 Crop Coefficients (Kc), Root Depths (m), and Depletion Fractions (p)
FAO56_CROP_PARAMETERS: dict[str, dict[str, Any]] = {
    "Cotton": {
        "kc": {"INITIAL": 0.35, "VEGETATIVE": 0.75, "FLOWERING": 1.20, "MATURITY": 0.65, "HARVEST": 0.50},
        "root_depth_min_m": 0.30,
        "root_depth_max_m": 1.20,
        "depletion_fraction_p": 0.65,
        "growth_stages_das": {"INITIAL": 25, "VEGETATIVE": 60, "FLOWERING": 105, "MATURITY": 150},
    },
    "Paddy": {
        "kc": {"INITIAL": 1.05, "VEGETATIVE": 1.15, "FLOWERING": 1.25, "MATURITY": 0.95, "HARVEST": 0.70},
        "root_depth_min_m": 0.20,
        "root_depth_max_m": 0.60,
        "depletion_fraction_p": 0.20,  # Flood ponding / sensitive
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 50, "FLOWERING": 90, "MATURITY": 120},
    },
    "Rice": {
        "kc": {"INITIAL": 1.05, "VEGETATIVE": 1.15, "FLOWERING": 1.25, "MATURITY": 0.95, "HARVEST": 0.70},
        "root_depth_min_m": 0.20,
        "root_depth_max_m": 0.60,
        "depletion_fraction_p": 0.20,
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 50, "FLOWERING": 90, "MATURITY": 120},
    },
    "Maize": {
        "kc": {"INITIAL": 0.30, "VEGETATIVE": 0.70, "FLOWERING": 1.20, "MATURITY": 0.50, "HARVEST": 0.35},
        "root_depth_min_m": 0.25,
        "root_depth_max_m": 1.00,
        "depletion_fraction_p": 0.55,
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 50, "FLOWERING": 85, "MATURITY": 115},
    },
    "Soybean": {
        "kc": {"INITIAL": 0.40, "VEGETATIVE": 0.80, "FLOWERING": 1.15, "MATURITY": 0.50, "HARVEST": 0.30},
        "root_depth_min_m": 0.25,
        "root_depth_max_m": 0.90,
        "depletion_fraction_p": 0.50,
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 45, "FLOWERING": 75, "MATURITY": 105},
    },
    "Wheat": {
        "kc": {"INITIAL": 0.30, "VEGETATIVE": 0.75, "FLOWERING": 1.15, "MATURITY": 0.40, "HARVEST": 0.25},
        "root_depth_min_m": 0.25,
        "root_depth_max_m": 1.10,
        "depletion_fraction_p": 0.55,
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 55, "FLOWERING": 95, "MATURITY": 130},
    },
    "Groundnut": {
        "kc": {"INITIAL": 0.40, "VEGETATIVE": 0.70, "FLOWERING": 1.15, "MATURITY": 0.60, "HARVEST": 0.40},
        "root_depth_min_m": 0.25,
        "root_depth_max_m": 0.80,
        "depletion_fraction_p": 0.50,
        "growth_stages_das": {"INITIAL": 25, "VEGETATIVE": 55, "FLOWERING": 90, "MATURITY": 125},
    },
    "Chana": {
        "kc": {"INITIAL": 0.40, "VEGETATIVE": 0.70, "FLOWERING": 1.05, "MATURITY": 0.45, "HARVEST": 0.30},
        "root_depth_min_m": 0.20,
        "root_depth_max_m": 0.75,
        "depletion_fraction_p": 0.50,
        "growth_stages_das": {"INITIAL": 20, "VEGETATIVE": 45, "FLOWERING": 75, "MATURITY": 105},
    },
}


def get_groundwater_fallback(district_name: str | None = None) -> float:
    """Resolve regional groundwater table depth in mbgl."""
    if not district_name:
        return DEFAULT_GROUNDWATER_DEPTH_MBGL
    normalized = district_name.strip().lower()
    return CGWB_DISTRICT_GROUNDWATER_MBGL.get(normalized, DEFAULT_GROUNDWATER_DEPTH_MBGL)


def get_soil_benchmark(soil_texture: str | None = None) -> dict[str, Any]:
    """Resolve regional soil physicochemical benchmark."""
    if not soil_texture or soil_texture not in SOIL_TYPE_BENCHMARKS:
        return SOIL_TYPE_BENCHMARKS["Vertisol"]
    return SOIL_TYPE_BENCHMARKS[soil_texture]


def get_crop_params(crop_name: str) -> dict[str, Any]:
    """Retrieve FAO-56 crop coefficients and growth parameters."""
    normalized = crop_name.strip().capitalize()
    return FAO56_CROP_PARAMETERS.get(normalized, FAO56_CROP_PARAMETERS["Cotton"])

