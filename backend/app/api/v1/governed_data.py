"""DPDP-Compliant Governed Data Products API Router.

Provides de-identified, spatially generalized aggregate data products for
Farmer Producer Organizations (FPOs), research institutions, and parametric crop insurance.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.governed_data import (
    FPOCropSummaryReport,
    ParametricInsuranceIndexReport,
)
from app.services.governed_data_service import GovernedDataService

router = APIRouter(prefix="/governed", tags=["Governed Data Products"])


@router.get("/fpo/crop-summary", response_model=FPOCropSummaryReport)
def get_fpo_crop_summary(
    district: Optional[str] = Query(None, description="Optional administrative district filter"),
    db: Session = Depends(get_db),
) -> FPOCropSummaryReport:
    """Retrieve de-identified collective crop acreage report aggregated by crop and variety."""
    return GovernedDataService.get_fpo_crop_summary(db=db, district=district)


@router.get("/insurance/drought-index", response_model=ParametricInsuranceIndexReport)
def get_parametric_drought_index(
    district: Optional[str] = Query(None, description="Optional region or district filter"),
    db: Session = Depends(get_db),
) -> ParametricInsuranceIndexReport:
    """Retrieve block-level parametric drought risk scores and insurance payout triggers."""
    return GovernedDataService.get_parametric_drought_index(db=db, district=district)

