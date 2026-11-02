"""Crop-Cycle Roadmap & Stage Checkpoints API Router.

Provides endpoints to view the active crop milestone roadmap, track phenological
stage progress, and complete or defer stage checkpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.engines.roadmap_engine import RoadmapEngine
from app.models.plot import CropCycle, FarmPlot
from app.models.workflows import RoadmapCheckpoint
from app.schemas.workflows import (
    CheckpointCompleteRequest,
    CropRoadmapResponse,
    RoadmapCheckpointResponse,
)

router = APIRouter(prefix="/plots", tags=["Crop-Cycle Roadmaps & Checkpoints"])


@router.get("/{plot_id}/roadmap", response_model=CropRoadmapResponse)
def get_plot_roadmap(
    plot_id: int,
    db: Session = Depends(get_db),
) -> CropRoadmapResponse:
    """Retrieve active crop milestone roadmap, phenological progress, and stage checkpoints."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")

    active_cycle = (
        db.query(CropCycle)
        .filter(CropCycle.plot_id == plot_id, CropCycle.is_active == True)
        .first()
    )

    roadmap = RoadmapEngine.get_or_create_roadmap(db, plot_id=plot_id, crop_cycle=active_cycle)
    return RoadmapEngine.format_roadmap_response(roadmap)


@router.post("/{plot_id}/checkpoints/{checkpoint_id}/complete", response_model=RoadmapCheckpointResponse)
def complete_roadmap_checkpoint(
    plot_id: int,
    checkpoint_id: int,
    payload: CheckpointCompleteRequest,
    db: Session = Depends(get_db),
) -> RoadmapCheckpointResponse:
    """Mark a roadmap milestone checkpoint as completed or deferred with field notes."""
    plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
    if not plot:
        raise EntityNotFoundError(f"Farm plot with ID {plot_id} not found.")

    checkpoint = db.query(RoadmapCheckpoint).filter(RoadmapCheckpoint.id == checkpoint_id).first()
    if not checkpoint:
        raise EntityNotFoundError(f"Roadmap checkpoint with ID {checkpoint_id} not found.")

    if checkpoint.roadmap.plot_id != plot_id:
        raise EntityNotFoundError(f"Checkpoint {checkpoint_id} does not belong to plot {plot_id}.")

    updated = RoadmapEngine.complete_checkpoint(
        db=db,
        checkpoint_id=checkpoint_id,
        notes=payload.notes,
        status=payload.status,
    )
    return RoadmapCheckpointResponse.model_validate(updated)

