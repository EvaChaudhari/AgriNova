"""Live Agricultural Context Builder.

Assembles the complete deterministic environmental and agronomic packet
for bootstrap state sync and LLM grounding.
"""

from datetime import date
from typing import Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.models.profile import DeviceProfile
from app.models.plot import FarmPlot, CropCycle
from app.models.telemetry import GroundwaterObservation, SoilHealthRecord
from app.services.fallback_data import (
    get_groundwater_fallback,
    get_soil_benchmark,
)
from app.services.weather_service import fetch_weather_data
from app.engines.fao56_hydrology import (
    calculate_fao56_et0,
    FAO56DailyET0Input,
    calculate_water_balance,
    WaterBalanceInput,
)
from app.engines.hazard_state import HazardStateMachine, HazardEngineInput
from app.engines.satellite_stac import fetch_sentinel2_indices


@dataclass
class AgriculturalContextPacket:
    """Consolidated environmental, hydrological, and agronomic snapshot."""
    device_id: str
    farmer_name: str
    preferred_language: str
    plot_id: int | None
    plot_name: str | None
    centroid: dict[str, float]
    area_hectares: float
    soil_texture: str
    crop_name: str
    variety: str | None
    growth_stage: str
    days_after_sowing: int
    groundwater: dict[str, Any]
    soil_nutrients: dict[str, Any]
    weather: dict[str, Any]
    satellite: dict[str, Any]
    hydrology: dict[str, Any]
    hazard: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def build_agricultural_context(
    db: Session,
    device_profile: DeviceProfile,
    plot: FarmPlot | None = None,
) -> AgriculturalContextPacket:
    """Concurrently resolve all environmental layers and execute scientific engines."""
    # 1. Resolve Active Plot and Crop
    if plot is None:
        plot = db.query(FarmPlot).filter(FarmPlot.device_id == device_profile.device_id, FarmPlot.is_active == True).first()

    crop_cycle: CropCycle | None = None
    if plot:
        crop_cycle = db.query(CropCycle).filter(CropCycle.plot_id == plot.id, CropCycle.is_active == True).first()

    crop_name = crop_cycle.crop_name if crop_cycle else "Cotton"
    growth_stage = crop_cycle.growth_stage if crop_cycle else "FLOWERING"
    variety = crop_cycle.variety if crop_cycle else "Hybrid Bt-Cotton"
    sowing_date = crop_cycle.sowing_date if crop_cycle else date.today()
    irrigation_method = crop_cycle.irrigation_method if crop_cycle else "DRIP"
    das = max(0, (date.today() - sowing_date).days)

    lat = plot.centroid_lat if plot else 17.5
    lon = plot.centroid_lon if plot else 78.5
    soil_texture = plot.soil_texture if plot else "Vertisol"
    slope_percent = plot.slope_percent if plot else 1.5

    # 2. Ingestion Hierarchy: Groundwater (Sensor -> WRIS -> Fallback)
    gw_depth: float
    gw_source: str
    gw_record = (
        db.query(GroundwaterObservation)
        .filter(GroundwaterObservation.plot_id == (plot.id if plot else None))
        .order_by(GroundwaterObservation.observation_date.desc())
        .first()
    ) if plot else None

    if gw_record:
        gw_depth = gw_record.depth_mbgl
        gw_source = gw_record.source_type
    else:
        gw_depth = get_groundwater_fallback(plot.name if plot else None)
        gw_source = "FALLBACK_DISTRICT"

    # 3. Ingestion Hierarchy: Weather (Live API -> Agro-Climatic Normal)
    weather = await fetch_weather_data(lat, lon)

    # 4. Ingestion Hierarchy: Soil Health (SHC API -> Regional Benchmark)
    shc_record = (
        db.query(SoilHealthRecord)
        .filter(SoilHealthRecord.plot_id == plot.id)
        .order_by(SoilHealthRecord.tested_date.desc())
        .first()
    ) if plot else None

    if shc_record:
        soil_nutrients = {
            "nitrogen_kg_ha": shc_record.nitrogen_kg_ha,
            "phosphorus_kg_ha": shc_record.phosphorus_kg_ha,
            "potassium_kg_ha": shc_record.potassium_kg_ha,
            "ph": shc_record.ph,
            "organic_carbon_percent": shc_record.organic_carbon_percent,
            "source": shc_record.source_type,
        }
    else:
        soil_bm = get_soil_benchmark(soil_texture)
        soil_nutrients = {
            "nitrogen_kg_ha": soil_bm["nitrogen_kg_ha"],
            "phosphorus_kg_ha": soil_bm["phosphorus_kg_ha"],
            "potassium_kg_ha": soil_bm["potassium_kg_ha"],
            "ph": soil_bm["ph"],
            "organic_carbon_percent": soil_bm["organic_carbon_percent"],
            "source": "REGIONAL_FALLBACK",
        }

    # 5. Ingestion Hierarchy: Satellite (Sentinel-2 STAC -> Synthetic Phenology)
    bbox = [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01]
    satellite_indices = await fetch_sentinel2_indices(bbox, crop_name, sowing_date)

    # 6. Execute FAO-56 Hydrological Engine
    fao_params = FAO56DailyET0Input(
        t_min=weather.t_min,
        t_max=weather.t_max,
        rh_mean=weather.rh_mean,
        wind_speed_2m=weather.wind_speed_2m,
        solar_radiation_mj_m2=weather.solar_radiation_mj_m2,
        elevation_m=plot.elevation_m if plot else 250.0,
        latitude_deg=lat,
        day_of_year=date.today().timetuple().tm_yday,
    )
    et0 = calculate_fao56_et0(fao_params)

    wb_inputs = WaterBalanceInput(
        crop_name=crop_name,
        growth_stage=growth_stage,
        soil_texture=soil_texture,
        et0_mm_day=et0,
        rainfall_24h_mm=weather.rainfall_24h_mm,
        previous_depletion_mm=30.0,  # Baseline rolling balance
        groundwater_depth_mbgl=gw_depth,
        irrigation_method=irrigation_method,
    )
    water_balance = calculate_water_balance(wb_inputs)

    # 7. Execute Extreme Weather Hazard State Machine
    hazard_inputs = HazardEngineInput(
        rainfall_forecast_24h_mm=weather.rainfall_24h_mm,
        groundwater_depth_mbgl=gw_depth,
        rainfall_deficit_percent=weather.seasonal_deficit_percent,
        dem_slope_percent=slope_percent,
        ndwi=satellite_indices.ndwi,
        waterlogged_reported=(water_balance.trigger == "DRAIN"),
    )
    hazard_result = HazardStateMachine.evaluate(hazard_inputs)

    return AgriculturalContextPacket(
        device_id=device_profile.device_id,
        farmer_name=device_profile.farmer_name,
        preferred_language=device_profile.preferred_language,
        plot_id=plot.id if plot else None,
        plot_name=plot.name if plot else None,
        centroid={"lat": lat, "lon": lon},
        area_hectares=plot.area_hectares if plot else 1.0,
        soil_texture=soil_texture,
        crop_name=crop_name,
        variety=variety,
        growth_stage=growth_stage,
        days_after_sowing=das,
        groundwater={
            "depth_mbgl": round(gw_depth, 2),
            "source": gw_source,
        },
        soil_nutrients=soil_nutrients,
        weather={
            "t_min": weather.t_min,
            "t_max": weather.t_max,
            "t_mean": weather.t_mean,
            "rh_mean": weather.rh_mean,
            "wind_speed_2m": weather.wind_speed_2m,
            "rainfall_24h_mm": weather.rainfall_24h_mm,
            "seasonal_deficit_percent": weather.seasonal_deficit_percent,
            "condition": weather.condition_description,
            "source": weather.source,
        },
        satellite={
            "ndvi": satellite_indices.ndvi,
            "ndwi": satellite_indices.ndwi,
            "source": satellite_indices.source,
            "cloud_cover_percent": satellite_indices.cloud_cover_percent,
            "details": satellite_indices.details,
        },
        hydrology={
            "et0_mm": water_balance.et0_mm,
            "kc": water_balance.kc,
            "etc_mm": water_balance.etc_mm,
            "root_depth_m": water_balance.root_depth_m,
            "taw_mm": water_balance.taw_mm,
            "raw_mm": water_balance.raw_mm,
            "depletion_mm": water_balance.root_zone_depletion_mm,
            "trigger": water_balance.trigger,
            "recommended_depth_mm": water_balance.recommended_depth_mm,
            "efficiency": water_balance.irrigation_efficiency,
            "details": water_balance.details,
        },
        hazard={
            "current_state": hazard_result.current_state,
            "is_critical_water_stress": hazard_result.is_critical_water_stress,
            "slope_risk": hazard_result.slope_risk,
            "enforced_restrictions": hazard_result.enforced_restrictions,
            "actionable_directives": hazard_result.actionable_directives,
            "summary_message": hazard_result.summary_message,
        },
    )

