"""Scientific Validation & MLOps Evaluation API Router.

Provides endpoints to run automated ICAR empirical benchmarks and inspect
plot-level telemetry completeness, freshness, and uncertainty quality scores.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.engines.evaluation_engine import EvaluationEngine
from app.schemas.evaluation import (
    PlotQualityReport,
    ScientificBenchmarkReport,
)

router = APIRouter(prefix="/evaluation", tags=["Scientific Evaluation & MLOps"])


@router.get("/scientific-benchmarks", response_model=ScientificBenchmarkReport)
def get_scientific_benchmarks() -> ScientificBenchmarkReport:
    """Run empirical benchmark validation suite against ICAR lysimeter reference datasets."""
    return EvaluationEngine.evaluate_scientific_benchmarks()


@router.get("/plot/{plot_id}/quality-report", response_model=PlotQualityReport)
def get_plot_quality_report(
    plot_id: int,
    db: Session = Depends(get_db),
) -> PlotQualityReport:
    """Evaluate telemetry completeness, sensor freshness, and agronomic uncertainty for a plot."""
    try:
        return EvaluationEngine.evaluate_plot_data_quality(db=db, plot_id=plot_id)
    except ValueError as exc:
        raise EntityNotFoundError(str(exc))

