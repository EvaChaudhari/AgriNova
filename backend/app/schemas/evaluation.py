"""Scientific Validation & MLOps Evaluation Schemas (Pydantic v2).

Defines data contracts for:
- Automated FAO-56 and phenological scientific benchmark verification
- Plot-level data completeness, sensor freshness, and anomaly quality scores
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ScientificBenchmarkItem(BaseModel):
    """Validation comparison against an empirical ICAR lysimeter benchmark."""

    benchmark_name: str
    agroclimatic_zone: str
    reference_value: float
    calculated_value: float
    absolute_error: float
    relative_error_percent: float
    tolerance_percent: float
    passed: bool


class ScientificBenchmarkReport(BaseModel):
    """Suite-level empirical verification report."""

    total_benchmarks: int
    passed_benchmarks: int
    all_passed: bool
    max_relative_error_percent: float
    benchmark_suite: str
    results: list[ScientificBenchmarkItem] = Field(default_factory=list)
    evaluated_at: datetime


class PlotQualityReport(BaseModel):
    """Plot-level telemetry quality, sensor freshness, and uncertainty assessment."""

    plot_id: int
    data_completeness_percent: float = Field(..., ge=0.0, le=100.0)
    sensor_freshness_hours: float = Field(..., ge=0.0)
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    agronomic_uncertainty_score: float = Field(..., ge=0.0, le=1.0)
    overall_quality_grade: str  # EXCELLENT, GOOD, ADEQUATE, DEGRADED
    data_layer_status: dict[str, str] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)

