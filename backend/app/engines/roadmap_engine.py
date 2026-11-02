"""Crop-Cycle Roadmap & Stage Checkpoint Engine.

Generates structured end-to-end agronomic milestone calendars for crop cycles,
evaluates phenological stage progress, and manages checkpoint completion status.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.crop_knowledge import Crop
from app.models.plot import CropCycle, FarmPlot
from app.models.workflows import CropRoadmap, RoadmapCheckpoint
from app.schemas.workflows import CropRoadmapResponse, RoadmapCheckpointResponse


class RoadmapEngine:
    """Agronomic milestone calendar and checkpoint manager."""

    # Standard 6-milestone blueprint parameterized by duration
    CHECKPOINT_BLUEPRINTS = [
        {
            "stage_name": "SOWING",
            "title": "Sowing & Seed Treatment",
            "description": "Treat seeds with Bio-fertilizers (Rhizobium/Azotobacter) and Trichoderma viride to prevent seed-borne pathogens. Maintain recommended row spacing.",
            "das_fraction": 0.0,
            "min_das": 0,
            "max_das": 0,
            "guidance": "Check seed viability before sowing. Ensure proper seed depth in moist soil.",
        },
        {
            "stage_name": "BASAL_FERTILIZATION",
            "title": "Basal Fertilizer Application",
            "description": "Broadcast or band-place 100% of recommended DAP and MOP, along with 1/3 dose of Urea as basal dose at or immediately following sowing.",
            "das_fraction": 0.02,
            "min_das": 1,
            "max_das": 3,
            "guidance": "Place fertilizer 5cm away and 5cm below the seed furrow to avoid seedling injury.",
        },
        {
            "stage_name": "WEEDING",
            "title": "Weed Control & Early Inter-cultivation",
            "description": "Perform mechanical hoeing or apply recommended selective pre/post-emergence herbicide to maintain critical weed-free period.",
            "das_fraction": 0.15,
            "min_das": 15,
            "max_das": 25,
            "guidance": "First 30 days are critical for weed competition. Inter-cultivation aerates soil and conserves moisture.",
        },
        {
            "stage_name": "VEGETATIVE_MANAGEMENT",
            "title": "Vegetative Water & 1st Top-Dressing",
            "description": "Apply 1st top-dressing of Urea with irrigation. Inspect canopy development and check for sucking pests (aphids, jassids, thrips).",
            "das_fraction": 0.30,
            "min_das": 30,
            "max_das": 45,
            "guidance": "Do not top-dress urea during waterlogged soil or before imminent heavy rainfall.",
        },
        {
            "stage_name": "FLOWERING_INSPECTION",
            "title": "Flowering Inspection & IPM Pest Scouting",
            "description": "Inspect peak flowering and panicle initiation. Critical moisture stress window — ensure soil moisture is at field capacity. Deploy pheromone traps for pest monitoring.",
            "das_fraction": 0.55,
            "min_das": 60,
            "max_das": 75,
            "guidance": "Water stress during flowering induces irreversible yield reduction. Check ETL before spraying any chemical.",
        },
        {
            "stage_name": "MATURITY_HARVEST",
            "title": "Pre-Harvest Water Cutoff & Maturity Check",
            "description": "Cut off irrigation 10-14 days before physiological maturity. Monitor grain/boll hardening and harvest under clear weather.",
            "das_fraction": 0.90,
            "min_das": 85,
            "max_das": 150,
            "guidance": "Early water cutoff prevents grain discoloration and promotes uniform field drying.",
        },
    ]

    @classmethod
    def get_or_create_roadmap(
        cls,
        db: Session,
        plot_id: int,
        crop_cycle: Optional[CropCycle] = None,
    ) -> CropRoadmap:
        """Fetch active roadmap for a plot or generate a new one from crop cycle parameters."""
        roadmap = (
            db.query(CropRoadmap)
            .filter(CropRoadmap.plot_id == plot_id, CropRoadmap.is_active == True)
            .first()
        )
        if roadmap:
            cls.update_roadmap_stage(db, roadmap)
            return roadmap

        # Resolve crop parameters
        if crop_cycle:
            crop_name = crop_cycle.crop_name
            variety_name = crop_cycle.variety
            sowing_date = crop_cycle.sowing_date
            cycle_id = crop_cycle.id
        else:
            plot = db.query(FarmPlot).filter(FarmPlot.id == plot_id).first()
            crop_name = "Cotton"
            variety_name = "Bt Cotton RCH-2"
            sowing_date = date.today() - timedelta(days=20)
            cycle_id = None

        # Look up crop duration in database
        crop_obj = db.query(Crop).filter(Crop.name.ilike(crop_name)).first()
        duration_days = crop_obj.standard_duration_days if crop_obj else 140
        harvest_date = sowing_date + timedelta(days=duration_days)

        # Create new roadmap
        roadmap = CropRoadmap(
            plot_id=plot_id,
            crop_cycle_id=cycle_id,
            crop_name=crop_name,
            variety_name=variety_name,
            sowing_date=sowing_date,
            expected_harvest_date=harvest_date,
            current_stage="INITIAL",
            total_checkpoints=len(cls.CHECKPOINT_BLUEPRINTS),
            completed_checkpoints=0,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(roadmap)
        db.flush()  # Populates roadmap.id

        # Generate the 6 milestones
        for bp in cls.CHECKPOINT_BLUEPRINTS:
            # Scaled DAS
            if bp["min_das"] == 0:
                target_das = 0
            else:
                target_das = int(round(duration_days * bp["das_fraction"]))
                target_das = max(bp["min_das"], min(bp["max_das"], target_das))

            target_date = sowing_date + timedelta(days=target_das)
            cp = RoadmapCheckpoint(
                roadmap_id=roadmap.id,
                stage_name=bp["stage_name"],
                title=bp["title"],
                description=bp["description"],
                target_day_after_sowing=target_das,
                target_date=target_date,
                status="PENDING",
                actionable_guidance=bp["guidance"],
            )
            db.add(cp)

        db.commit()
        db.refresh(roadmap)
        cls.update_roadmap_stage(db, roadmap)
        return roadmap

    @classmethod
    def update_roadmap_stage(cls, db: Session, roadmap: CropRoadmap) -> None:
        """Update current phenological stage and completed checkpoint counter."""
        das = (date.today() - roadmap.sowing_date).days

        # Query crop growth stages from DB if available
        crop_obj = db.query(Crop).filter(Crop.name.ilike(roadmap.crop_name)).first()
        if crop_obj and crop_obj.growth_stages:
            stages = sorted(crop_obj.growth_stages, key=lambda s: s.start_das)
            current_stage = stages[0].stage_name
            for s in stages:
                if s.start_das <= das <= s.end_das:
                    current_stage = s.stage_name
                    break
            roadmap.current_stage = current_stage
        else:
            # Fallback phenology
            if das < 25:
                roadmap.current_stage = "INITIAL"
            elif das < 60:
                roadmap.current_stage = "VEGETATIVE"
            elif das < 105:
                roadmap.current_stage = "FLOWERING"
            else:
                roadmap.current_stage = "MATURITY"

        completed = sum(1 for cp in roadmap.checkpoints if cp.status == "COMPLETED")
        roadmap.completed_checkpoints = completed
        roadmap.updated_at = datetime.now(timezone.utc)
        db.commit()

    @classmethod
    def complete_checkpoint(
        cls,
        db: Session,
        checkpoint_id: int,
        notes: Optional[str] = None,
        status: str = "COMPLETED",
    ) -> RoadmapCheckpoint:
        """Mark a checkpoint as completed or deferred."""
        cp = db.query(RoadmapCheckpoint).filter(RoadmapCheckpoint.id == checkpoint_id).first()
        if not cp:
            raise ValueError(f"Checkpoint with ID {checkpoint_id} not found.")

        cp.status = status.upper().strip()
        cp.completed_at = datetime.now(timezone.utc)
        if notes:
            cp.notes = notes.strip()

        db.commit()
        db.refresh(cp)

        # Refresh roadmap parent statistics
        cls.update_roadmap_stage(db, cp.roadmap)
        return cp

    @classmethod
    def format_roadmap_response(cls, roadmap: CropRoadmap) -> CropRoadmapResponse:
        """Serialize CropRoadmap model into CropRoadmapResponse schema."""
        das = max(0, (date.today() - roadmap.sowing_date).days)
        progress = (
            round((roadmap.completed_checkpoints / roadmap.total_checkpoints) * 100.0, 1)
            if roadmap.total_checkpoints > 0
            else 0.0
        )

        return CropRoadmapResponse(
            id=roadmap.id,
            plot_id=roadmap.plot_id,
            crop_cycle_id=roadmap.crop_cycle_id,
            crop_name=roadmap.crop_name,
            variety_name=roadmap.variety_name,
            sowing_date=roadmap.sowing_date,
            expected_harvest_date=roadmap.expected_harvest_date,
            current_stage=roadmap.current_stage,
            days_after_sowing=das,
            total_checkpoints=roadmap.total_checkpoints,
            completed_checkpoints=roadmap.completed_checkpoints,
            progress_percent=progress,
            checkpoints=[
                RoadmapCheckpointResponse.model_validate(cp)
                for cp in roadmap.checkpoints
            ],
        )

