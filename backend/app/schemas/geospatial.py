"""Geospatial and Plot schemas (Pydantic v2)."""

from typing import Literal, Optional, Any
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="List of rings: [[ [lon1, lat1], [lon2, lat2], ..., [lon1, lat1] ]]"
    )


class PlotCreateRequest(BaseModel):
    device_id: str
    name: str = Field(..., min_length=1, max_length=120)
    survey_number: Optional[str] = None
    khasra_number: Optional[str] = None
    boundary: GeoJSONPolygon
    soil_texture: str = Field(default="Vertisol")
    elevation_m: float = Field(default=250.0)
    slope_percent: float = Field(default=1.5)


class PlotResponse(BaseModel):
    id: int
    device_id: str
    name: str
    survey_number: Optional[str] = None
    khasra_number: Optional[str] = None
    centroid_lat: float
    centroid_lon: float
    area_hectares: float
    soil_texture: str
    elevation_m: float
    slope_percent: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CropCycleCreateRequest(BaseModel):
    crop_name: str
    variety: Optional[str] = None
    sowing_date: date
    growth_stage: str = Field(default="INITIAL")  # INITIAL, VEGETATIVE, FLOWERING, MATURITY, HARVEST
    irrigation_method: str = Field(default="DRIP")  # DRIP, SPRINKLER, FLOOD, RAINFED
    expected_harvest_date: Optional[date] = None


class CropCycleResponse(BaseModel):
    id: int
    plot_id: int
    crop_name: str
    variety: Optional[str] = None
    sowing_date: date
    growth_stage: str
    irrigation_method: str
    is_active: bool
    expected_harvest_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroundwaterCreateRequest(BaseModel):
    depth_mbgl: float
    source_type: str = Field(default="HARDWARE_SENSOR")


class GroundwaterResponse(BaseModel):
    id: int
    plot_id: Optional[int] = None
    depth_mbgl: float
    source_type: str
    observation_date: datetime

    model_config = ConfigDict(from_attributes=True)


class SoilHealthCreateRequest(BaseModel):
    nitrogen_kg_ha: float
    phosphorus_kg_ha: float
    potassium_kg_ha: float
    ph: float
    organic_carbon_percent: float
    source_type: str = Field(default="SOIL_HEALTH_CARD_API")


class SoilHealthResponse(BaseModel):
    id: int
    plot_id: int
    nitrogen_kg_ha: float
    phosphorus_kg_ha: float
    potassium_kg_ha: float
    ph: float
    organic_carbon_percent: float
    source_type: str
    tested_date: date

    model_config = ConfigDict(from_attributes=True)

