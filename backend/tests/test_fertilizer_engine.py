"""Unit Tests for ICAR STCR Fertilizer Engine (Milestone D).

Validates qualitative soil fertility classification, composite Soil Health Index,
ICAR STCR targeted yield equations, commercial 50kg bag equivalents, and safe dosage clamping.
"""

import pytest
from app.engines.fertilizer_engine import (
    FertilizerEngine,
    NutrientRating,
    FertilizerRecommendationResult,
)


def test_classify_soil_health_low_fertility_acidic():
    """Verify classification of low fertility soil with acidic pH."""
    rating = FertilizerEngine.classify_soil_health(
        nitrogen_kg_ha=180.0,
        phosphorus_kg_ha=10.0,
        potassium_kg_ha=110.0,
        ph=5.8,
        organic_carbon_percent=0.35,
    )

    assert rating.nitrogen_rating == "LOW"
    assert rating.phosphorus_rating == "LOW"
    assert rating.potassium_rating == "LOW"
    assert rating.organic_carbon_rating == "LOW"
    assert rating.ph_classification == "ACIDIC"
    assert "lime" in rating.soil_amendment_directive.lower()
    assert 0.0 <= rating.soil_health_index <= 100.0
    assert rating.soil_health_index < 50.0


def test_classify_soil_health_medium_neutral():
    """Verify classification of balanced medium fertility soil with neutral pH."""
    rating = FertilizerEngine.classify_soil_health(
        nitrogen_kg_ha=320.0,
        phosphorus_kg_ha=20.0,
        potassium_kg_ha=200.0,
        ph=7.2,
        organic_carbon_percent=0.60,
    )

    assert rating.nitrogen_rating == "MEDIUM"
    assert rating.phosphorus_rating == "MEDIUM"
    assert rating.potassium_rating == "MEDIUM"
    assert rating.organic_carbon_rating == "MEDIUM"
    assert rating.ph_classification == "NEUTRAL"
    assert rating.soil_amendment_directive is None
    assert rating.soil_health_index >= 70.0


def test_classify_soil_health_high_sodic():
    """Verify classification of high fertility soil with sodic pH."""
    rating = FertilizerEngine.classify_soil_health(
        nitrogen_kg_ha=620.0,
        phosphorus_kg_ha=35.0,
        potassium_kg_ha=320.0,
        ph=8.8,
        organic_carbon_percent=0.85,
    )

    assert rating.nitrogen_rating == "HIGH"
    assert rating.phosphorus_rating == "HIGH"
    assert rating.potassium_rating == "HIGH"
    assert rating.organic_carbon_rating == "HIGH"
    assert rating.ph_classification == "SODIC"
    assert "gypsum" in rating.soil_amendment_directive.lower()


def test_calculate_stcr_fertilizer_cotton_balanced():
    """Verify ICAR STCR fertilizer requirement calculation for Cotton with commercial bag conversions."""
    # STCR coefficients for Cotton:
    # FN = 4.40 * T - 0.38 * SN
    # FP = 1.80 * T - 0.45 * SP
    # FK = 2.10 * T - 0.18 * SK
    stcr_coeffs = {
        "stcr_a_n": 4.40, "stcr_b_n": 0.38,
        "stcr_a_p": 1.80, "stcr_b_p": 0.45,
        "stcr_a_k": 2.10, "stcr_b_k": 0.18,
    }
    max_bounds = {
        "max_n_kg_ha": 150.0,
        "max_p_kg_ha": 75.0,
        "max_k_kg_ha": 75.0,
    }

    result = FertilizerEngine.calculate_stcr_fertilizer(
        crop_name="Cotton",
        target_yield_q_ha=25.0,
        soil_n_kg_ha=200.0,
        soil_p_kg_ha=15.0,
        soil_k_kg_ha=180.0,
        stcr_coeffs=stcr_coeffs,
        max_bounds=max_bounds,
        field_area_ha=2.0,
        soil_ph=7.4,
        organic_carbon_pct=0.55,
    )

    # Expected raw:
    # N = 4.40 * 25 - 0.38 * 200 = 110.0 - 76.0 = 34.0 kg/ha
    # P = 1.80 * 25 - 0.45 * 15 = 45.0 - 6.75 = 38.25 -> 38.2 kg/ha
    # K = 2.10 * 25 - 0.18 * 180 = 52.5 - 32.4 = 20.1 kg/ha
    assert result.recommended_n_kg_ha == pytest.approx(34.0, abs=0.5)
    assert result.recommended_p_kg_ha == pytest.approx(38.2, abs=0.5)
    assert result.recommended_k_kg_ha == pytest.approx(20.1, abs=0.5)
    assert result.is_clamped_to_safe_max is False

    # Commercial conversions:
    # DAP (46% P2O5) = 38.2 / 0.46 = 83.0 kg/ha -> 1.7 bags/ha
    # N from DAP = 83.0 * 0.18 = 14.9 kg/ha
    # Net Urea N = 34.0 - 14.9 = 19.1 kg/ha -> Urea = 19.1 / 0.46 = 41.5 kg/ha -> 0.8 bags/ha
    # MOP (60% K2O) = 20.1 / 0.60 = 33.5 kg/ha -> 0.7 bags/ha
    assert result.total_dap_bags_50kg > 0
    assert result.total_urea_bags_50kg > 0
    assert result.total_mop_bags_50kg > 0

    # Field area scaling: 2.0 ha = 2x
    assert result.field_total_dap_bags == pytest.approx(result.total_dap_bags_50kg * 2.0, abs=0.2)
    assert result.field_total_urea_bags == pytest.approx(result.total_urea_bags_50kg * 2.0, abs=0.2)
    assert result.field_total_mop_bags == pytest.approx(result.total_mop_bags_50kg * 2.0, abs=0.2)

    # Split application schedule
    assert len(result.split_schedule) == 3
    stages = [item.growth_stage for item in result.split_schedule]
    assert "BASAL_SOWING" in stages
    assert "VEGETATIVE_STAGE" in stages
    assert "FLOWERING_STAGE" in stages

    # All DAP applied basal
    basal = [item for item in result.split_schedule if item.growth_stage == "BASAL_SOWING"][0]
    assert basal.dap_bags == result.total_dap_bags_50kg


def test_calculate_stcr_fertilizer_safe_clamping_prevents_overdose():
    """Verify that unrealistic high target yield is strictly clamped to ICAR safe upper bounds."""
    stcr_coeffs = {
        "stcr_a_n": 5.0, "stcr_b_n": 0.1,
        "stcr_a_p": 2.5, "stcr_b_p": 0.1,
        "stcr_a_k": 3.0, "stcr_b_k": 0.1,
    }
    max_bounds = {
        "max_n_kg_ha": 150.0,
        "max_p_kg_ha": 75.0,
        "max_k_kg_ha": 75.0,
    }

    # Yield 100 q/ha would raw calculate N = 500 - 10 = 490 kg/ha!
    result = FertilizerEngine.calculate_stcr_fertilizer(
        crop_name="Cotton",
        target_yield_q_ha=100.0,
        soil_n_kg_ha=100.0,
        soil_p_kg_ha=10.0,
        soil_k_kg_ha=100.0,
        stcr_coeffs=stcr_coeffs,
        max_bounds=max_bounds,
    )

    assert result.is_clamped_to_safe_max is True
    assert result.recommended_n_kg_ha == 150.0
    assert result.recommended_p_kg_ha == 75.0
    assert result.recommended_k_kg_ha == 75.0
    assert any("clamped" in note.lower() for note in result.advisory_notes)


def test_calculate_stcr_fertilizer_high_soil_fertility_zero_dose():
    """Verify that high native soil test values clamp negative requirements to zero."""
    stcr_coeffs = {
        "stcr_a_n": 4.40, "stcr_b_n": 0.38,
        "stcr_a_p": 1.80, "stcr_b_p": 0.45,
        "stcr_a_k": 2.10, "stcr_b_k": 0.18,
    }
    max_bounds = {
        "max_n_kg_ha": 150.0,
        "max_p_kg_ha": 75.0,
        "max_k_kg_ha": 75.0,
    }

    # Extremely high soil nutrient reservoir
    result = FertilizerEngine.calculate_stcr_fertilizer(
        crop_name="Cotton",
        target_yield_q_ha=15.0,
        soil_n_kg_ha=500.0,
        soil_p_kg_ha=100.0,
        soil_k_kg_ha=400.0,
        stcr_coeffs=stcr_coeffs,
        max_bounds=max_bounds,
    )

    assert result.recommended_n_kg_ha == 0.0
    assert result.recommended_p_kg_ha == 0.0
    assert result.recommended_k_kg_ha == 0.0
    assert result.total_dap_bags_50kg == 0.0
    assert result.total_urea_bags_50kg == 0.0
    assert result.total_mop_bags_50kg == 0.0

