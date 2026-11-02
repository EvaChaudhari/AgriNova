"""ICAR Soil Test Crop Response (STCR) Fertilizer Engine.

Calculates targeted-yield nutrient requirements, converts pure N-P-K into commercial
50kg fertilizer bag equivalents (Urea, DAP, MOP), and generates stage-wise split
application schedules with strict ICAR safe maximum clamping.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Optional


@dataclass(frozen=True)
class NutrientRating:
    """Qualitative classification of soil fertility parameters."""

    nitrogen_rating: str  # LOW, MEDIUM, HIGH
    phosphorus_rating: str  # LOW, MEDIUM, HIGH
    potassium_rating: str  # LOW, MEDIUM, HIGH
    organic_carbon_rating: str  # LOW, MEDIUM, HIGH
    ph_classification: str  # ACIDIC, NEUTRAL, ALKALINE, SODIC
    soil_health_index: float  # Composite 0 - 100 score
    soil_amendment_directive: Optional[str] = None


@dataclass(frozen=True)
class SplitApplicationItem:
    """Stage-wise commercial fertilizer application instructions."""

    growth_stage: str  # BASAL_SOWING, VEGETATIVE_STAGE, FLOWERING_STAGE
    timing_das: str
    dap_bags: float
    urea_bags: float
    mop_bags: float
    instructions: str


@dataclass(frozen=True)
class FertilizerRecommendationResult:
    """Final targeted yield fertilizer advisory with bag conversions and safety limits."""

    crop_name: str
    target_yield_q_ha: float
    
    # Pure elemental/oxide nutrients (kg/ha)
    recommended_n_kg_ha: float
    recommended_p_kg_ha: float
    recommended_k_kg_ha: float
    is_clamped_to_safe_max: bool
    
    # Commercial 50kg bag equivalents (per hectare)
    total_dap_bags_50kg: float
    total_urea_bags_50kg: float
    total_mop_bags_50kg: float
    
    # Commercial bag equivalents scaled to field area
    field_area_hectares: float
    field_total_dap_bags: float
    field_total_urea_bags: float
    field_total_mop_bags: float
    
    # Agronomic schedule & safety warnings
    split_schedule: list[SplitApplicationItem] = field(default_factory=list)
    soil_rating: Optional[NutrientRating] = None
    advisory_notes: list[str] = field(default_factory=list)


class FertilizerEngine:
    """Deterministic agronomic calculator for soil test ratings and STCR equations."""

    # ICAR Standard Soil Testing Manual Thresholds
    N_LOW_THRESHOLD = 280.0
    N_HIGH_THRESHOLD = 560.0

    P_LOW_THRESHOLD = 14.0
    P_HIGH_THRESHOLD = 28.0

    K_LOW_THRESHOLD = 140.0
    K_HIGH_THRESHOLD = 280.0

    OC_LOW_THRESHOLD = 0.50
    OC_HIGH_THRESHOLD = 0.75

    @classmethod
    def classify_soil_health(
        cls,
        nitrogen_kg_ha: float,
        phosphorus_kg_ha: float,
        potassium_kg_ha: float,
        ph: float,
        organic_carbon_percent: float,
    ) -> NutrientRating:
        """Classify soil test parameters into qualitative fertility tiers."""
        # Nitrogen
        if nitrogen_kg_ha < cls.N_LOW_THRESHOLD:
            n_rate = "LOW"
            n_score = 40.0
        elif nitrogen_kg_ha <= cls.N_HIGH_THRESHOLD:
            n_rate = "MEDIUM"
            n_score = 75.0
        else:
            n_rate = "HIGH"
            n_score = 95.0

        # Phosphorus
        if phosphorus_kg_ha < cls.P_LOW_THRESHOLD:
            p_rate = "LOW"
            p_score = 40.0
        elif phosphorus_kg_ha <= cls.P_HIGH_THRESHOLD:
            p_rate = "MEDIUM"
            p_score = 75.0
        else:
            p_rate = "HIGH"
            p_score = 95.0

        # Potassium
        if potassium_kg_ha < cls.K_LOW_THRESHOLD:
            k_rate = "LOW"
            k_score = 40.0
        elif potassium_kg_ha <= cls.K_HIGH_THRESHOLD:
            k_rate = "MEDIUM"
            k_score = 75.0
        else:
            k_rate = "HIGH"
            k_score = 95.0

        # Organic Carbon
        if organic_carbon_percent < cls.OC_LOW_THRESHOLD:
            oc_rate = "LOW"
            oc_score = 35.0
        elif organic_carbon_percent <= cls.OC_HIGH_THRESHOLD:
            oc_rate = "MEDIUM"
            oc_score = 70.0
        else:
            oc_rate = "HIGH"
            oc_score = 95.0

        # pH classification
        amendment = None
        if ph < 6.5:
            ph_class = "ACIDIC"
            ph_score = 50.0
            amendment = "Soil is acidic. Apply agricultural lime (calcium carbonate) or dolomite at 2-4 q/ha to raise pH."
        elif ph <= 7.8:
            ph_class = "NEUTRAL"
            ph_score = 95.0
        elif ph <= 8.5:
            ph_class = "ALKALINE"
            ph_score = 70.0
            amendment = "Soil is moderately alkaline. Apply well-decomposed FYM/compost and consider sulfur or gypsum."
        else:
            ph_class = "SODIC"
            ph_score = 35.0
            amendment = "Soil is sodic (pH > 8.5). Apply agricultural gypsum based on GR value and ensure deep drainage."

        # Composite Soil Health Index (0-100)
        shi = round(
            0.25 * n_score + 0.20 * p_score + 0.15 * k_score + 0.25 * oc_score + 0.15 * ph_score,
            1,
        )

        return NutrientRating(
            nitrogen_rating=n_rate,
            phosphorus_rating=p_rate,
            potassium_rating=k_rate,
            organic_carbon_rating=oc_rate,
            ph_classification=ph_class,
            soil_health_index=shi,
            soil_amendment_directive=amendment,
        )

    @classmethod
    def calculate_stcr_fertilizer(
        cls,
        crop_name: str,
        target_yield_q_ha: float,
        soil_n_kg_ha: float,
        soil_p_kg_ha: float,
        soil_k_kg_ha: float,
        stcr_coeffs: dict[str, float],
        max_bounds: dict[str, float],
        field_area_ha: float = 1.0,
        soil_ph: float = 7.5,
        organic_carbon_pct: float = 0.50,
    ) -> FertilizerRecommendationResult:
        """Compute ICAR STCR fertilizer requirement with safe bounds and commercial bag conversion.

        Equation: Fertilizer Dose (kg/ha) = A * TargetYield - B * SoilTestValue
        Commercial Conversions:
        - DAP: 18% N, 46% P2O5
        - Urea: 46% N
        - MOP: 60% K2O
        """
        # 1. Evaluate STCR Raw Formulas
        raw_n = stcr_coeffs["stcr_a_n"] * target_yield_q_ha - stcr_coeffs["stcr_b_n"] * soil_n_kg_ha
        raw_p = stcr_coeffs["stcr_a_p"] * target_yield_q_ha - stcr_coeffs["stcr_b_p"] * soil_p_kg_ha
        raw_k = stcr_coeffs["stcr_a_k"] * target_yield_q_ha - stcr_coeffs["stcr_b_k"] * soil_k_kg_ha

        # Clamping to [0, max_safe]
        max_n = max_bounds.get("max_n_kg_ha", 220.0)
        max_p = max_bounds.get("max_p_kg_ha", 100.0)
        max_k = max_bounds.get("max_k_kg_ha", 100.0)

        clamped = (
            raw_n > max_n or raw_p > max_p or raw_k > max_k
            or raw_n < 0 or raw_p < 0 or raw_k < 0
        )

        n_req = max(0.0, min(max_n, round(raw_n, 1)))
        p_req = max(0.0, min(max_p, round(raw_p, 1)))
        k_req = max(0.0, min(max_k, round(raw_k, 1)))

        # 2. Commercial Fertilizer Bag Translations
        # A) DAP supplies 46% P2O5 and 18% N
        if p_req > 0:
            dap_kg_ha = p_req / 0.46
            n_from_dap_ha = dap_kg_ha * 0.18
        else:
            dap_kg_ha = 0.0
            n_from_dap_ha = 0.0

        # B) Urea supplies 46% N (net after DAP contribution)
        remaining_n_ha = max(0.0, n_req - n_from_dap_ha)
        urea_kg_ha = remaining_n_ha / 0.46 if remaining_n_ha > 0 else 0.0

        # C) MOP supplies 60% K2O
        mop_kg_ha = k_req / 0.60 if k_req > 0 else 0.0

        # Bags per hectare (50kg bag)
        dap_bags_ha = round(dap_kg_ha / 50.0, 1)
        urea_bags_ha = round(urea_kg_ha / 50.0, 1)
        mop_bags_ha = round(mop_kg_ha / 50.0, 1)

        # Scale to field acreage
        field_dap = round(dap_bags_ha * field_area_ha, 1)
        field_urea = round(urea_bags_ha * field_area_ha, 1)
        field_mop = round(mop_bags_ha * field_area_ha, 1)

        # 3. Stage-Wise Split Schedule
        # Basal: 100% DAP, 100% MOP, ~30% Urea
        basal_urea = round(urea_bags_ha * 0.33, 1)
        veg_urea = round(urea_bags_ha * 0.34, 1)
        flower_urea = round(max(0.0, urea_bags_ha - basal_urea - veg_urea), 1)

        schedule = [
            SplitApplicationItem(
                growth_stage="BASAL_SOWING",
                timing_das="At sowing / field preparation (0 DAS)",
                dap_bags=dap_bags_ha,
                urea_bags=basal_urea,
                mop_bags=mop_bags_ha,
                instructions="Drill full DAP and MOP with 1/3rd Urea 5cm below and beside the seed line.",
            ),
            SplitApplicationItem(
                growth_stage="VEGETATIVE_STAGE",
                timing_das="First top-dressing (30 - 45 DAS)",
                dap_bags=0.0,
                urea_bags=veg_urea,
                mop_bags=0.0,
                instructions="Apply Urea top-dressing followed by light irrigation. Avoid broadcasting in standing water.",
            ),
            SplitApplicationItem(
                growth_stage="FLOWERING_STAGE",
                timing_das="Second top-dressing (60 - 75 DAS)",
                dap_bags=0.0,
                urea_bags=flower_urea,
                mop_bags=0.0,
                instructions="Top-dress remaining Urea at flowering/panicle initiation stage with adequate soil moisture.",
            ),
        ]

        # 4. Soil Health Classification
        rating = cls.classify_soil_health(
            nitrogen_kg_ha=soil_n_kg_ha,
            phosphorus_kg_ha=soil_p_kg_ha,
            potassium_kg_ha=soil_k_kg_ha,
            ph=soil_ph,
            organic_carbon_percent=organic_carbon_pct,
        )

        notes = [
            f"STCR target yield model for {crop_name} calibrated for {target_yield_q_ha} q/ha.",
            "All chemical doses bounded strictly by ICAR state agricultural university maximum limits.",
        ]
        if clamped:
            notes.append("One or more nutrient doses were clamped to ICAR maximum safe application thresholds to prevent toxicity and burning.")
        if rating.soil_amendment_directive:
            notes.append(rating.soil_amendment_directive)

        return FertilizerRecommendationResult(
            crop_name=crop_name,
            target_yield_q_ha=target_yield_q_ha,
            recommended_n_kg_ha=n_req,
            recommended_p_kg_ha=p_req,
            recommended_k_kg_ha=k_req,
            is_clamped_to_safe_max=clamped,
            total_dap_bags_50kg=dap_bags_ha,
            total_urea_bags_50kg=urea_bags_ha,
            total_mop_bags_50kg=mop_bags_ha,
            field_area_hectares=field_area_ha,
            field_total_dap_bags=field_dap,
            field_total_urea_bags=field_urea,
            field_total_mop_bags=field_mop,
            split_schedule=schedule,
            soil_rating=rating,
            advisory_notes=notes,
        )
