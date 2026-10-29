"""Extreme Weather Hazard State Engine.

Implements a deterministic finite state machine (FSM) prioritizing farmer safety,
crop protection, and resource conservation with strict agro-climatic overrides.
"""

from typing import Literal
from dataclasses import dataclass, field


HazardStateMode = Literal["NORMAL_MODE", "STORM_FLOOD_MODE", "EL_NINO_DROUGHT_MODE"]


@dataclass(frozen=True)
class HazardEngineInput:
    """Environmental parameters evaluated by the hazard state machine."""
    rainfall_forecast_24h_mm: float
    groundwater_depth_mbgl: float
    rainfall_deficit_percent: float
    dem_slope_percent: float = 1.5
    ndwi: float | None = None
    waterlogged_reported: bool = False


@dataclass
class HazardEvaluationResult:
    """Structured directive output from the hazard state machine."""
    current_state: HazardStateMode
    is_critical_water_stress: bool = False
    slope_risk: str | None = None  # HIGH_TOPSOIL_EROSION_RISK or ROOT_ASPHYXIATION_RISK
    enforced_restrictions: list[str] = field(default_factory=list)
    actionable_directives: list[str] = field(default_factory=list)
    summary_message: str = ""


class HazardStateMachine:
    """Deterministic finite state machine evaluating meteorological and hydrological risks."""

    # Explicit threshold constants
    STORM_RAINFALL_THRESHOLD_MM = 50.0
    EL_NINO_GROUNDWATER_THRESHOLD_MBGL = 18.0
    EL_NINO_RAINFALL_DEFICIT_THRESHOLD_PCT = 35.0
    CRITICAL_NDWI_THRESHOLD = -0.20
    SLOPE_EROSION_THRESHOLD_PCT = 3.0

    @classmethod
    def evaluate(cls, inputs: HazardEngineInput) -> HazardEvaluationResult:
        """Evaluate input state and return state mode with enforced directives."""
        # Priority 1: STORM_FLOOD_MODE
        if inputs.rainfall_forecast_24h_mm >= cls.STORM_RAINFALL_THRESHOLD_MM or inputs.waterlogged_reported:
            restrictions = [
                "HALT_ALL_CHEMICAL_SPRAYING",
                "HALT_FERTILIZERS",
                "CLEAR_DRAINAGE_FURROWS",
            ]

            # Analyze DEM terrain slope
            if inputs.dem_slope_percent > cls.SLOPE_EROSION_THRESHOLD_PCT:
                slope_risk = "HIGH_TOPSOIL_EROSION_RISK"
                slope_directive = (
                    f"Slope is {inputs.dem_slope_percent:.1f}% (>3%). High risk of topsoil sheet wash. "
                    f"Do not disturb soil; secure contour bunds immediately."
                )
            else:
                slope_risk = "ROOT_ASPHYXIATION_RISK"
                slope_directive = (
                    f"Low slope ({inputs.dem_slope_percent:.1f}%). High risk of water stagnation and root asphyxiation. "
                    f"Dig urgent drainage channels to divert stagnant water."
                )

            directives = [
                "Immediately cease all pesticide, fungicide, and herbicide spraying to prevent catastrophic runoff into groundwater.",
                "Halt all granular fertilizer top-dressing (urea/DAP) to avoid nutrient leaching.",
                "Ensure drainage furrows and field outlets are unobstructed.",
                slope_directive,
            ]

            summary = (
                f"STORM ALERT: 24-hour rainfall forecast is {inputs.rainfall_forecast_24h_mm:.1f} mm "
                f"(>= {cls.STORM_RAINFALL_THRESHOLD_MM} mm). All chemical applications suspended. "
                f"Terrain status: {slope_risk}."
            )

            return HazardEvaluationResult(
                current_state="STORM_FLOOD_MODE",
                is_critical_water_stress=False,
                slope_risk=slope_risk,
                enforced_restrictions=restrictions,
                actionable_directives=directives,
                summary_message=summary,
            )

        # Priority 2: EL_NINO_DROUGHT_MODE
        if (
            inputs.groundwater_depth_mbgl > cls.EL_NINO_GROUNDWATER_THRESHOLD_MBGL
            and inputs.rainfall_deficit_percent > cls.EL_NINO_RAINFALL_DEFICIT_THRESHOLD_PCT
        ):
            restrictions = [
                "FORBID_SURFACE_FLOOD_IRRIGATION",
            ]

            directives = [
                "Strictly prohibit surface flood or furrow basin flooding to conserve depleted aquifers.",
                "Operate drip or micro-sprinkler irrigation exclusively during night hours (8 PM - 5 AM) to minimize evaporative losses.",
                "Apply organic biomass/straw mulch (5-7 cm thickness) across crop beds to suppress soil evaporation.",
                "Plan short-duration, drought-resilient intercrops (green gram, cowpea, or pearl millet) to stabilize soil biology.",
            ]

            # Sub-mode: CRITICAL_WATER_STRESS
            critical_stress = False
            if inputs.ndwi is not None and inputs.ndwi < cls.CRITICAL_NDWI_THRESHOLD:
                critical_stress = True
                restrictions.append("ENFORCE_DEFICIT_IRRIGATION_ONLY")
                directives.insert(
                    0,
                    f"CRITICAL WATER STRESS DETECTED (NDWI: {inputs.ndwi:.2f} < {cls.CRITICAL_NDWI_THRESHOLD}). "
                    f"Execute emergency deficit irrigation to preserve root crown survival. "
                    f"Apply kaolin clay foliar spray (5%) to reduce plant transpiration.",
                )

            summary = (
                f"DROUGHT / EL NIÑO ALERT: Regional groundwater is at {inputs.groundwater_depth_mbgl:.1f} mbgl "
                f"(> {cls.EL_NINO_GROUNDWATER_THRESHOLD_MBGL} mbgl) with a seasonal rainfall deficit of "
                f"{inputs.rainfall_deficit_percent:.1f}% (> {cls.EL_NINO_RAINFALL_DEFICIT_THRESHOLD_PCT}%). "
                f"Surface flood irrigation is forbidden."
            )
            if critical_stress:
                summary += " CRITICAL CANOPY WATER STRESS ACTIVE."

            return HazardEvaluationResult(
                current_state="EL_NINO_DROUGHT_MODE",
                is_critical_water_stress=critical_stress,
                slope_risk=None,
                enforced_restrictions=restrictions,
                actionable_directives=directives,
                summary_message=summary,
            )

        # Priority 3: NORMAL_MODE
        return HazardEvaluationResult(
            current_state="NORMAL_MODE",
            is_critical_water_stress=False,
            slope_risk=None,
            enforced_restrictions=[],
            actionable_directives=[
                "Follow standard recommended FAO-56 irrigation and fertigation schedules.",
                "Conduct regular field scouting for pests and weed flushes.",
            ],
            summary_message="NORMAL OPERATING CONDITIONS: Weather and hydrological indicators are within standard parameters.",
        )

