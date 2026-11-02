"""Multi-Criteria Crop Suitability & Planning Engine.

Evaluates candidate crop agronomic suitability based on:
- Soil texture, drainage, and pH compatibility
- Water access: groundwater depth, irrigation infrastructure, and seasonal rainfall
- Water consumption penalties for thirsty crops (Sugarcane, Paddy) under water stress
- Variety selection from the database seeded in Milestone D
"""

from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.crop_knowledge import Crop, CropVariety
from app.schemas.workflows import CropSuitabilityItem


class CropPlannerEngine:
    """Scientific multi-criteria decision engine for crop suitability ranking."""

    # Soil texture affinities (base score out of 100)
    SOIL_AFFINITY_MATRIX: dict[str, dict[str, float]] = {
        "Vertisol": {
            "Cotton": 95.0,
            "Soybean": 92.0,
            "Chickpea": 90.0,
            "Wheat": 82.0,
            "Sugarcane": 78.0,
            "Maize": 75.0,
            "Mustard": 70.0,
            "Paddy": 60.0,
        },
        "Alluvial": {
            "Wheat": 95.0,
            "Paddy": 95.0,
            "Mustard": 90.0,
            "Maize": 88.0,
            "Sugarcane": 85.0,
            "Cotton": 72.0,
            "Soybean": 72.0,
            "Chickpea": 80.0,
        },
        "Inceptisol": {
            "Wheat": 90.0,
            "Paddy": 90.0,
            "Maize": 88.0,
            "Mustard": 85.0,
            "Chickpea": 82.0,
            "Cotton": 75.0,
            "Soybean": 75.0,
            "Sugarcane": 70.0,
        },
        "Alfisol": {
            "Chickpea": 88.0,
            "Mustard": 85.0,
            "Maize": 82.0,
            "Cotton": 75.0,
            "Soybean": 72.0,
            "Wheat": 68.0,
            "Sugarcane": 60.0,
            "Paddy": 55.0,
        },
        "Sandy Loam": {
            "Mustard": 90.0,
            "Chickpea": 85.0,
            "Maize": 82.0,
            "Wheat": 75.0,
            "Cotton": 70.0,
            "Soybean": 68.0,
            "Sugarcane": 50.0,
            "Paddy": 45.0,
        },
    }

    # Crop seasonal appropriateness
    CROP_SEASONS: dict[str, set[str]] = {
        "Cotton": {"KHARIF"},
        "Paddy": {"KHARIF", "ZAID"},
        "Wheat": {"RABI"},
        "Soybean": {"KHARIF"},
        "Maize": {"KHARIF", "RABI", "ZAID"},
        "Chickpea": {"RABI"},
        "Mustard": {"RABI"},
        "Sugarcane": {"KHARIF", "RABI", "ZAID"},  # Perennial
    }

    # Water requirement classification
    HIGH_WATER_CROPS = {"Sugarcane", "Paddy"}
    MEDIUM_WATER_CROPS = {"Cotton", "Wheat", "Maize", "Soybean"}
    LOW_WATER_CROPS = {"Chickpea", "Mustard"}

    @classmethod
    def evaluate_crop_suitability(
        cls,
        db: Session,
        soil_texture: str,
        soil_ph: float,
        groundwater_depth_mbgl: float,
        irrigation_method: str,
        season: str,
        preferred_category: Optional[str] = None,
    ) -> list[CropSuitabilityItem]:
        """Rank candidate crops for a plot using multi-criteria suitability scoring."""
        target_season = season.upper().strip()
        all_crops = db.query(Crop).filter(Crop.is_active == True).all()

        results: list[CropSuitabilityItem] = []

        for crop in all_crops:
            # 1. Season check
            valid_seasons = cls.CROP_SEASONS.get(crop.name, {crop.season})
            if target_season not in valid_seasons and target_season != "ALL":
                continue

            # Category filter
            if preferred_category and crop.category != preferred_category.upper().strip():
                continue

            # 2. Soil score
            tex_map = cls.SOIL_AFFINITY_MATRIX.get(soil_texture, {})
            base_soil_score = tex_map.get(crop.name, 70.0)

            # pH penalty (optimal is 6.5 - 8.0)
            ph_penalty = 0.0
            if soil_ph < 6.0:
                ph_penalty = (6.0 - soil_ph) * 12.0
            elif soil_ph > 8.2:
                ph_penalty = (soil_ph - 8.2) * 15.0

            soil_score = max(20.0, min(100.0, round(base_soil_score - ph_penalty, 1)))

            # 3. Water access score
            limiting_factors: list[str] = []

            # Base infrastructure water capacity
            irrig_upper = irrigation_method.upper().strip()
            if irrig_upper == "DRIP":
                base_water = 90.0
            elif irrig_upper == "SPRINKLER":
                base_water = 80.0
            elif irrig_upper == "FLOOD":
                base_water = 65.0
            else:  # RAINFED
                base_water = 40.0
                limiting_factors.append("Plot lacks dedicated micro-irrigation (rainfed cultivation)")

            # Groundwater availability modifier
            if groundwater_depth_mbgl > 18.0:
                limiting_factors.append(f"Deep regional groundwater table ({groundwater_depth_mbgl:.1f} mbgl)")
                gw_modifier = -25.0
            elif groundwater_depth_mbgl > 12.0:
                gw_modifier = -10.0
            elif groundwater_depth_mbgl < 6.0:
                gw_modifier = 10.0
            else:
                gw_modifier = 0.0

            effective_water_avail = max(10.0, min(100.0, base_water + gw_modifier))

            # Crop-specific water penalty or boost
            if crop.name in cls.HIGH_WATER_CROPS:
                if groundwater_depth_mbgl > 18.0 or irrig_upper == "RAINFED":
                    # Severe penalty for thirsty crops when water is scarce
                    water_score = max(15.0, effective_water_avail * 0.40)
                    limiting_factors.append(f"{crop.name} requires perennial irrigation (>1200mm); high drought failure risk")
                else:
                    water_score = effective_water_avail * 0.85
            elif crop.name in cls.LOW_WATER_CROPS:
                # Resilient crops maintain high water score even in rainfed conditions
                water_score = min(98.0, effective_water_avail * 1.25)
            else:
                water_score = effective_water_avail

            water_score = max(10.0, min(100.0, round(water_score, 1)))

            # 4. Composite Suitability Score
            # 45% Soil + 45% Water + 10% Seasonal alignment
            composite_score = round(0.45 * soil_score + 0.45 * water_score + 10.0, 1)
            composite_score = max(0.0, min(100.0, composite_score))

            # 5. Risk Categorization
            if composite_score >= 75.0:
                risk_category = "OPTIMAL"
                rationale = f"Highly suited for {soil_texture} soil and current water access."
            elif composite_score >= 50.0:
                risk_category = "SUITABLE_WITH_IRRIGATION"
                rationale = f"Feasible if timely supplemental irrigation and nutrients are provided."
            else:
                risk_category = "HIGH_RISK_DROUGHT"
                rationale = f"High failure risk under current moisture and groundwater constraints."

            # 6. Fetch recommended varieties
            varieties = [v.variety_name for v in crop.varieties]
            # Prioritize drought tolerant varieties if water is constrained
            if water_score < 60.0:
                drought_vars = [v.variety_name for v in crop.varieties if v.drought_tolerance in ("HIGH", "MEDIUM")]
                if drought_vars:
                    varieties = drought_vars

            results.append(
                CropSuitabilityItem(
                    crop_name=crop.name,
                    scientific_name=crop.scientific_name,
                    season=crop.season,
                    category=crop.category,
                    suitability_score=composite_score,
                    risk_category=risk_category,
                    water_access_score=water_score,
                    soil_compatibility_score=soil_score,
                    expected_duration_days=crop.standard_duration_days,
                    limiting_factors=limiting_factors,
                    recommended_varieties=varieties[:3],
                    rationale=rationale,
                )
            )

        # Sort descending by suitability score
        results.sort(key=lambda x: x.suitability_score, reverse=True)
        return results

