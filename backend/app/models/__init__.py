"""Database models package."""

from app.models.profile import DeviceProfile
from app.models.auth import User, Device
from app.models.consent import ConsentRecord, AuditLog
from app.models.plot import Farm, FarmPlot, CropCycle
from app.models.telemetry import GroundwaterObservation, SoilHealthRecord
from app.models.chat import ChatSession, ChatMessage
from app.models.observations import (
    WeatherObservation,
    WeatherForecast,
    SatelliteObservation,
    GroundwaterTimeSeries,
    TerrainTopography,
)
from app.models.crop_knowledge import (
    Crop,
    CropVariety,
    CropGrowthStage,
    CropNutrientBenchmark,
    CropPestProfile,
)

__all__ = [
    "DeviceProfile",
    "User",
    "Device",
    "ConsentRecord",
    "AuditLog",
    "Farm",
    "FarmPlot",
    "CropCycle",
    "GroundwaterObservation",
    "SoilHealthRecord",
    "ChatSession",
    "ChatMessage",
    "WeatherObservation",
    "WeatherForecast",
    "SatelliteObservation",
    "GroundwaterTimeSeries",
    "TerrainTopography",
    "Crop",
    "CropVariety",
    "CropGrowthStage",
    "CropNutrientBenchmark",
    "CropPestProfile",
]
