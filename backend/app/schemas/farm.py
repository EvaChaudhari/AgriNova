"""Farm holding and Multi-Plot management schemas (Pydantic v2)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.geospatial import PlotResponse


class FarmCreate(BaseModel):
    """Payload to register a parent agricultural holding."""

    name: str = Field(..., min_length=1, max_length=120, description="Farm holding name (e.g. Ganga Farm)")
    village: Optional[str] = Field(default=None, max_length=120)
    subdistrict: Optional[str] = Field(default=None, max_length=120)
    district: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    device_id: Optional[str] = Field(default=None, max_length=128)


class FarmUpdate(BaseModel):
    """Payload to update an existing farm holding."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    village: Optional[str] = Field(default=None, max_length=120)
    subdistrict: Optional[str] = Field(default=None, max_length=120)
    district: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    is_active: Optional[bool] = None


class FarmResponse(BaseModel):
    """Parent farm holding metadata with aggregate metrics."""

    id: int
    user_id: Optional[int] = None
    device_id: Optional[str] = None
    name: str
    village: Optional[str] = None
    subdistrict: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    total_area_hectares: float = 0.0
    plot_count: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MultiPlotResponse(BaseModel):
    """Parent farm holding with all associated child plots and land metrics."""

    farm: FarmResponse
    plots: list[PlotResponse] = []
    total_area_hectares: float = 0.0
    active_plots_count: int = 0

