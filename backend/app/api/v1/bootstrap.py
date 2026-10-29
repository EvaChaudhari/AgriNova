"""Bootstrap & State Sync API Endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.profile import DeviceProfile
from app.models.plot import FarmPlot
from app.schemas.bootstrap import BootstrapResponse, DeviceProfileCreate, DeviceProfileResponse
from app.services.context_builder import build_agricultural_context

router = APIRouter(prefix="/bootstrap", tags=["Bootstrap"])


@router.get("", response_model=BootstrapResponse)
async def bootstrap_app(
    device_id: str = Query(..., description="Unique hardware device identifier"),
    db: Session = Depends(get_db),
) -> BootstrapResponse:
    """App startup bootstrap endpoint.

    Resolves device profile, active farm plot, live environmental layers,
    and runs deterministic scientific hydrological and hazard state engines.
    """
    profile = db.query(DeviceProfile).filter(DeviceProfile.device_id == device_id).first()

    if not profile:
        return BootstrapResponse(
            device_id=device_id,
            is_onboarded=False,
            message="Device profile not found. Please complete farmer onboarding.",
            profile=None,
            active_plot_id=None,
            context=None,
            hazard_state=None,
            enforced_restrictions=[],
        )

    # Load active plot
    active_plot = db.query(FarmPlot).filter(FarmPlot.device_id == device_id, FarmPlot.is_active == True).first()

    # Build live agricultural context packet
    context_packet = await build_agricultural_context(db, profile, active_plot)
    packet_dict = context_packet.to_dict()

    return BootstrapResponse(
        device_id=device_id,
        is_onboarded=True,
        message="Device profile synchronized with live agro-climatic context.",
        profile=DeviceProfileResponse.model_validate(profile),
        active_plot_id=active_plot.id if active_plot else None,
        context=packet_dict,
        hazard_state=packet_dict["hazard"]["current_state"],
        enforced_restrictions=packet_dict["hazard"]["enforced_restrictions"],
    )


@router.post("/onboard", response_model=DeviceProfileResponse, status_code=status.HTTP_201_CREATED)
def onboard_device(
    payload: DeviceProfileCreate,
    db: Session = Depends(get_db),
) -> DeviceProfileResponse:
    """Register or update farmer profile for hardware device (one profile per device)."""
    existing = db.query(DeviceProfile).filter(DeviceProfile.device_id == payload.device_id).first()
    if existing:
        existing.farmer_name = payload.farmer_name
        existing.preferred_language = payload.preferred_language
        existing.phone_number = payload.phone_number
        existing.kisan_id = payload.kisan_id
        db.commit()
        db.refresh(existing)
        return DeviceProfileResponse.model_validate(existing)

    new_profile = DeviceProfile(
        device_id=payload.device_id,
        farmer_name=payload.farmer_name,
        preferred_language=payload.preferred_language,
        phone_number=payload.phone_number,
        kisan_id=payload.kisan_id,
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return DeviceProfileResponse.model_validate(new_profile)

