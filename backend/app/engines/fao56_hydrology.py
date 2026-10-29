"""FAO-56 Penman-Monteith Evapotranspiration and Soil Water Balance Engine.

Pure deterministic scientific engine implementing the Food and Agriculture Organization (FAO)
Irrigation and Drainage Paper No. 56 mathematical framework.
"""

import math
from typing import Literal
from dataclasses import dataclass

from app.services.fallback_data import get_soil_benchmark, get_crop_params


@dataclass(frozen=True)
class FAO56DailyET0Input:
    """Input parameters for FAO-56 Penman-Monteith daily reference evapotranspiration."""
    t_min: float  # Minimum air temperature [°C]
    t_max: float  # Maximum air temperature [°C]
    rh_mean: float  # Mean relative humidity [%] (or derived from max/min)
    wind_speed_2m: float  # Wind speed at 2 m height [m/s]
    solar_radiation_mj_m2: float | None = None  # Solar radiation Rs [MJ m-2 day-1]
    elevation_m: float = 250.0  # Elevation above sea level [m]
    latitude_deg: float = 17.5  # Latitude [decimal degrees]
    day_of_year: int = 180  # Julian Day of the year [1-366]


@dataclass(frozen=True)
class WaterBalanceInput:
    """Input parameters for soil water balance depletion modeling."""
    crop_name: str
    growth_stage: str  # INITIAL, VEGETATIVE, FLOWERING, MATURITY, HARVEST
    soil_texture: str
    et0_mm_day: float
    rainfall_24h_mm: float = 0.0
    previous_depletion_mm: float = 0.0
    groundwater_depth_mbgl: float = 12.0
    irrigation_method: str = "DRIP"  # DRIP, SPRINKLER, FLOOD, RAINFED


@dataclass(frozen=True)
class WaterBalanceOutput:
    """Result of FAO-56 hydrological water balance and categorical trigger."""
    et0_mm: float
    kc: float
    etc_mm: float
    root_depth_m: float
    taw_mm: float  # Total Available Water
    raw_mm: float  # Readily Available Water
    effective_rain_mm: float
    capillary_rise_mm: float
    root_zone_depletion_mm: float
    trigger: Literal["IRRIGATE", "DRAIN", "HOLD"]
    recommended_depth_mm: float
    irrigation_efficiency: float
    details: str


def calculate_fao56_et0(params: FAO56DailyET0Input) -> float:
    """Calculate daily Reference Evapotranspiration (ET0) using FAO-56 Penman-Monteith.

    Formula:
        ET0 = (0.408 * Delta * (Rn - G) + gamma * (900 / (T_mean + 273)) * u2 * (es - ea))
              / (Delta + gamma * (1 + 0.34 * u2))
    """
    t_min = params.t_min
    t_max = params.t_max
    t_mean = (t_max + t_min) / 2.0
    z = params.elevation_m
    u2 = max(0.1, params.wind_speed_2m)

    # 1. Atmospheric pressure (P in kPa)
    p = 101.3 * math.pow((293.0 - 0.0065 * z) / 293.0, 5.26)

    # 2. Psychrometric constant (gamma in kPa/°C)
    gamma = 0.000665 * p

    # 3. Saturation vapor pressure (es in kPa)
    def sat_vp(temp: float) -> float:
        return 0.6108 * math.exp((17.27 * temp) / (temp + 237.3))

    es_tmax = sat_vp(t_max)
    es_tmin = sat_vp(t_min)
    es = (es_tmax + es_tmin) / 2.0

    # 4. Actual vapor pressure (ea in kPa)
    ea = (params.rh_mean / 100.0) * es
    ea = min(ea, es)  # Cannot exceed saturation

    # 5. Slope of saturation vapor pressure curve (Delta in kPa/°C)
    delta = (4098.0 * (0.6108 * math.exp((17.27 * t_mean) / (t_mean + 237.3)))) / math.pow(t_mean + 237.3, 2)

    # 6. Extraterrestrial radiation (Ra in MJ m-2 day-1)
    phi = math.radians(params.latitude_deg)
    j = params.day_of_year
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * j / 365.0)
    solar_dec = 0.409 * math.sin((2.0 * math.pi * j / 365.0) - 1.39)

    tan_term = -math.tan(phi) * math.tan(solar_dec)
    tan_term = max(-1.0, min(1.0, tan_term))
    omega_s = math.acos(tan_term)

    g_sc = 0.0820  # MJ m-2 min-1
    ra = ((24.0 * 60.0) / math.pi) * g_sc * dr * (
        omega_s * math.sin(phi) * math.sin(solar_dec)
        + math.cos(phi) * math.cos(solar_dec) * math.sin(omega_s)
    )

    # 7. Clear sky solar radiation (Rso in MJ m-2 day-1)
    rso = (0.75 + 2e-5 * z) * ra

    # 8. Solar radiation (Rs)
    if params.solar_radiation_mj_m2 is not None and params.solar_radiation_mj_m2 > 0:
        rs = params.solar_radiation_mj_m2
    else:
        # Hargreaves radiation approximation from temp range
        k_rs = 0.16  # Interior coefficient
        rs = k_rs * math.sqrt(max(0.1, t_max - t_min)) * ra

    # 9. Net solar shortwave radiation (Rns) for grass albedo = 0.23
    rns = (1.0 - 0.23) * rs

    # 10. Net longwave radiation (Rnl)
    sigma = 4.903e-9  # Stefan-Boltzmann constant MJ K-4 m-2 day-1
    t_max_k4 = math.pow(t_max + 273.16, 4)
    t_min_k4 = math.pow(t_min + 273.16, 4)
    rs_ratio = rs / max(0.001, rso)
    rs_ratio = max(0.3, min(1.0, rs_ratio))

    rnl = (
        sigma
        * ((t_max_k4 + t_min_k4) / 2.0)
        * (0.34 - 0.14 * math.sqrt(max(0.0, ea)))
        * (1.35 * rs_ratio - 0.35)
    )

    # 11. Net radiation (Rn in MJ m-2 day-1) and daily Soil Heat Flux (G = 0)
    rn = rns - rnl
    g = 0.0

    # 12. FAO-56 Penman-Monteith equation
    numerator = 0.408 * delta * (rn - g) + gamma * (900.0 / (t_mean + 273.0)) * u2 * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * u2)

    et0 = numerator / denominator
    return max(0.0, round(et0, 2))


def calculate_effective_rainfall(rainfall_mm: float) -> float:
    """Calculate effective rainfall (P_eff) available for root zone infiltration.

    Accounting for surface canopy interception and surface runoff.
    """
    if rainfall_mm <= 5.0:
        return 0.0
    elif rainfall_mm <= 50.0:
        return round(0.8 * (rainfall_mm - 5.0), 2)
    else:
        # Extreme storm event: heavy runoff fraction
        return round(0.8 * 45.0 + 0.3 * (rainfall_mm - 50.0), 2)


def calculate_capillary_rise(groundwater_depth_mbgl: float, soil_texture: str) -> float:
    """Estimate daily capillary rise contribution from shallow groundwater table."""
    if groundwater_depth_mbgl > 2.0:
        return 0.0
    elif groundwater_depth_mbgl > 1.0:
        # Moderate shallow water table
        return 0.8 if soil_texture in ("Vertisol", "Clay Loam") else 0.4
    else:
        # High water table (< 1 mbgl)
        return 1.8 if soil_texture in ("Vertisol", "Clay Loam") else 1.0


def calculate_water_balance(inputs: WaterBalanceInput) -> WaterBalanceOutput:
    """Execute complete FAO-56 soil water balance and generate categorical trigger."""
    # Retrieve crop and soil parameters
    crop_info = get_crop_params(inputs.crop_name)
    soil_info = get_soil_benchmark(inputs.soil_texture)

    stage_key = inputs.growth_stage.upper()
    kc = crop_info["kc"].get(stage_key, crop_info["kc"]["VEGETATIVE"])

    # Root depth calculation
    z_min = crop_info["root_depth_min_m"]
    z_max = crop_info["root_depth_max_m"]
    if stage_key == "INITIAL":
        root_depth_m = z_min
    elif stage_key == "VEGETATIVE":
        root_depth_m = (z_min + z_max) / 2.0
    else:
        root_depth_m = z_max

    # Crop evapotranspiration ETc
    etc_mm = round(kc * inputs.et0_mm_day, 2)

    # Total Available Water (TAW) and Readily Available Water (RAW)
    theta_fc = soil_info["field_capacity"]
    theta_wp = soil_info["wilting_point"]
    taw_mm = round(1000.0 * (theta_fc - theta_wp) * root_depth_m, 2)

    depletion_fraction_p = crop_info["depletion_fraction_p"]
    # Depletion fraction adjustment for high ETc (> 5 mm/day): p_adj = p + 0.04 * (5 - ETc)
    p_adj = max(0.1, min(0.8, depletion_fraction_p + 0.04 * (5.0 - etc_mm)))
    raw_mm = round(p_adj * taw_mm, 2)

    # Inflow and Outflows
    p_eff = calculate_effective_rainfall(inputs.rainfall_24h_mm)
    gw_cap = calculate_capillary_rise(inputs.groundwater_depth_mbgl, inputs.soil_texture)

    # Water balance depletion update: D_t = D_{t-1} + ETc - P_eff - GW_cap
    net_depletion_change = etc_mm - p_eff - gw_cap
    new_depletion_mm = inputs.previous_depletion_mm + net_depletion_change

    # Irrigation efficiency by application method
    efficiencies = {
        "DRIP": 0.90,
        "SPRINKLER": 0.75,
        "FLOOD": 0.60,
        "RAINFED": 1.0,
    }
    eff = efficiencies.get(inputs.irrigation_method.upper(), 0.85)

    # Categorical trigger decision logic
    if new_depletion_mm < -15.0 or (inputs.rainfall_24h_mm >= 50.0 and inputs.soil_texture == "Vertisol"):
        # Excess water risk: oversaturated root zone
        trigger = "DRAIN"
        rec_depth_mm = 0.0
        final_depletion_mm = 0.0
        details = (
            f"Oversaturation detected (effective rainfall {p_eff} mm exceeds soil holding capacity). "
            f"Drain excess furrow water to prevent root asphyxiation."
        )
    elif new_depletion_mm >= raw_mm:
        # Readily Available Water exhausted: trigger irrigation
        trigger = "IRRIGATE"
        final_depletion_mm = min(taw_mm, max(0.0, new_depletion_mm))
        # Gross irrigation depth required to bring soil to field capacity
        rec_depth_mm = round(final_depletion_mm / eff, 1)
        details = (
            f"Soil root depletion ({final_depletion_mm:.1f} mm) exceeds RAW threshold ({raw_mm:.1f} mm). "
            f"Apply {rec_depth_mm:.1f} mm via {inputs.irrigation_method}."
        )
    else:
        # Soil moisture is within healthy buffering capacity
        trigger = "HOLD"
        rec_depth_mm = 0.0
        final_depletion_mm = max(0.0, round(new_depletion_mm, 1))
        details = (
            f"Soil water depletion ({final_depletion_mm:.1f} mm) is within buffer (RAW: {raw_mm:.1f} mm). "
            f"Irrigation not required today."
        )

    return WaterBalanceOutput(
        et0_mm=inputs.et0_mm_day,
        kc=kc,
        etc_mm=etc_mm,
        root_depth_m=round(root_depth_m, 2),
        taw_mm=taw_mm,
        raw_mm=raw_mm,
        effective_rain_mm=p_eff,
        capillary_rise_mm=gw_cap,
        root_zone_depletion_mm=final_depletion_mm,
        trigger=trigger,
        recommended_depth_mm=rec_depth_mm,
        irrigation_efficiency=eff,
        details=details,
    )

