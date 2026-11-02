"""Farm Holding & Multi-Plot Management Endpoints.

Allows farmers to manage parent agricultural holdings and register multiple contiguous
or disjoint plots within a single farm boundary.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import (
    Identity,
    get_current_identity,
    get_required_identity,
    record_audit_log,
)
from app.core.database import get_db
from app.core.exceptions import (
    EntityNotFoundError,
    ForbiddenActionError,
    UnauthorizedAccessError,
)
from app.models.plot import Farm, FarmPlot
from app.schemas.farm import (
    FarmCreate,
    FarmResponse,
    FarmUpdate,
    MultiPlotResponse,
)
from app.schemas.geospatial import PlotResponse

router = APIRouter(prefix="/farms", tags=["Farm Holdings & Multi-Plot Management"])


def _verify_farm_access(farm: Farm, identity: Identity) -> None:
    """Verify that current caller owns or has device authority over the farm."""
    if identity.user and farm.user_id == identity.user.id:
        return
    if identity.device_id and farm.device_id == identity.device_id:
        return
    raise ForbiddenActionError(f"You do not have permission to access farm holding {farm.id}.")


@router.post("", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    request: Request,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> FarmResponse:
    """Register a new parent farm holding for aggregating multiple plots."""
    user_id = identity.id if identity.user else None
    dev_id = payload.device_id or identity.device_id

    farm = Farm(
        name=payload.name,
        village=payload.village,
        subdistrict=payload.subdistrict,
        district=payload.district,
        state=payload.state,
        user_id=user_id,
        device_id=dev_id,
        total_area_hectares=0.0,
        is_active=True,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)

    ip_addr = request.client.host if request.client else None
    record_audit_log(
        db,
        action="FARM_CREATED",
        resource_type="farm",
        resource_id=str(farm.id),
        user_id=user_id,
        device_id=dev_id,
        details={"name": farm.name, "district": farm.district},
        ip_address=ip_addr,
    )

    resp = FarmResponse.model_validate(farm)
    resp.plot_count = 0
    return resp


@router.get("", response_model=list[FarmResponse])
def list_farms(
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> list[FarmResponse]:
    """List all registered farm holdings for the authenticated farmer or hardware device."""
    user_id = identity.id if identity.user else None
    dev_id = identity.device_id

    query = db.query(Farm).filter(Farm.is_active.is_(True))
    if user_id:
        farms = query.filter(Farm.user_id == user_id).all()
    elif dev_id:
        farms = query.filter(Farm.device_id == dev_id).all()
    else:
        farms = []

    result: list[FarmResponse] = []
    for f in farms:
        active_plots = [p for p in f.plots if p.is_active]
        total_ha = round(sum(p.area_hectares for p in active_plots), 2)
        resp = FarmResponse.model_validate(f)
        resp.plot_count = len(active_plots)
        resp.total_area_hectares = total_ha
        result.append(resp)

    return result


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(
    farm_id: int,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> FarmResponse:
    """Retrieve details and aggregated acreage of a specific farm holding."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise EntityNotFoundError(f"Farm holding with ID {farm_id} not found.")

    _verify_farm_access(farm, identity)

    active_plots = [p for p in farm.plots if p.is_active]
    total_ha = round(sum(p.area_hectares for p in active_plots), 2)
    resp = FarmResponse.model_validate(farm)
    resp.plot_count = len(active_plots)
    resp.total_area_hectares = total_ha
    return resp


@router.get("/{farm_id}/plots", response_model=MultiPlotResponse)
def get_farm_multi_plots(
    farm_id: int,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> MultiPlotResponse:
    """Retrieve all plots associated with a parent farm holding."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise EntityNotFoundError(f"Farm holding with ID {farm_id} not found.")

    _verify_farm_access(farm, identity)

    plots = db.query(FarmPlot).filter(FarmPlot.farm_id == farm_id).order_by(FarmPlot.id.desc()).all()
    active_plots = [p for p in plots if p.is_active]
    total_ha = round(sum(p.area_hectares for p in active_plots), 2)

    farm_resp = FarmResponse.model_validate(farm)
    farm_resp.plot_count = len(active_plots)
    farm_resp.total_area_hectares = total_ha

    return MultiPlotResponse(
        farm=farm_resp,
        plots=[PlotResponse.model_validate(p) for p in plots],
        total_area_hectares=total_ha,
        active_plots_count=len(active_plots),
    )


@router.delete("/{farm_id}", status_code=status.HTTP_200_OK)
def delete_farm(
    farm_id: int,
    request: Request,
    identity: Identity = Depends(get_required_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Deactivate a farm holding and its associated plots."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise EntityNotFoundError(f"Farm holding with ID {farm_id} not found.")

    _verify_farm_access(farm, identity)

    farm.is_active = False
    for plot in farm.plots:
        plot.is_active = False

    db.commit()

    ip_addr = request.client.host if request.client else None
    record_audit_log(
        db,
        action="FARM_DEACTIVATED",
        resource_type="farm",
        resource_id=str(farm.id),
        user_id=identity.id if identity.user else None,
        device_id=identity.device_id,
        details={"farm_id": farm.id, "name": farm.name},
        ip_address=ip_addr,
    )

    return {"status": "deactivated", "farm_id": farm_id}
