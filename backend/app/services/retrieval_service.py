"""Approved Agronomic Knowledge Retrieval Service (RAG Grounding).

Manages vetted ICAR / State Agricultural University Packages of Practices (PoP),
injecting authoritative citations and certified management directives into conversational models.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.workflows import ApprovedAgronomicGuide

logger = logging.getLogger("agrinova.retrieval")

BASELINE_ICAR_GUIDES = [
    {
        "crop_name": "Cotton",
        "category": "NUTRIENT_MANAGEMENT",
        "stage_name": "FLOWERING",
        "icar_recommendation": "Foliar spray of 2% DAP or 1% KNO3 (Potassium Nitrate) twice during peak flowering and boll formation at 15-day intervals significantly reduces square and boll drop.",
        "citation_source": "ICAR-CICR Nagpur Cotton Production Technology Bulletin No. 42 (2023)",
    },
    {
        "crop_name": "Cotton",
        "category": "IPM_DISEASE_PEST",
        "stage_name": "FLOWERING",
        "icar_recommendation": "For Pink Bollworm management, install 5 pheromone traps/ha at 45 DAS. When moth catch exceeds ETL of 8 moths/trap/night for 3 consecutive days, spray Profenofos 50 EC @ 2ml/L or Emamectin Benzoate 5 SG @ 0.4g/L.",
        "citation_source": "CIB&RC Major Uses of Pesticides (Fibre Crops) & CICR Annual Advisory (2024)",
    },
    {
        "crop_name": "Paddy",
        "category": "WATER_MANAGEMENT",
        "stage_name": "VEGETATIVE",
        "icar_recommendation": "Adopt Alternate Wetting and Drying (AWD) irrigation using a field water tube (pani pipe). Re-irrigate to 5cm ponded depth only when water level drops to 15cm below soil surface, saving up to 30% water without yield penalty.",
        "citation_source": "ICAR-NRRI Cuttack AWD Implementation Guidelines for Rice Farmers (2023)",
    },
    {
        "crop_name": "Wheat",
        "category": "IRRIGATION",
        "stage_name": "INITIAL",
        "icar_recommendation": "Crown Root Initiation (CRI) stage (20-25 DAS) is the most critical stage for wheat irrigation. Delaying CRI irrigation by even one week causes irreversible tillering reduction and up to 30% yield loss.",
        "citation_source": "ICAR-IIWBR Karnal Wheat Package of Practices for NWPZ & NEPZ (2024)",
    },
    {
        "crop_name": "Soybean",
        "category": "SOIL_PREPARATION",
        "stage_name": "SOWING",
        "icar_recommendation": "In Vertisols susceptible to waterlogging, construct Broad Bed and Furrow (BBF) or Ridge and Furrow system at 45cm row spacing to facilitate in-situ soil moisture conservation and excess drainage.",
        "citation_source": "ICAR-IISR Indore Soybean Production Guide Bulletin 18 (2023)",
    },
    {
        "crop_name": "Chickpea",
        "category": "IPM_DISEASE_PEST",
        "stage_name": "FLOWERING",
        "icar_recommendation": "For Pod Borer (Helicoverpa armigera), erect 50 bird perches/ha and spray Bacillus thuringiensis (Bt) @ 1.5kg/ha at early instar stage. Chemical intervention: Chlorantraniliprole 18.5 SC @ 0.3ml/L.",
        "citation_source": "ICAR-IIPR Kanpur Pulse Protection Manual (2023)",
    },
]


class AgronomicRetrievalService:
    """Retrieval service grounding conversational AI responses with verified ICAR citations."""

    @classmethod
    def seed_guides_if_empty(cls, db: Session) -> int:
        """Seed baseline approved guides if table is empty."""
        existing_count = db.query(ApprovedAgronomicGuide).count()
        if existing_count >= len(BASELINE_ICAR_GUIDES):
            return existing_count

        inserted = 0
        for g in BASELINE_ICAR_GUIDES:
            existing = (
                db.query(ApprovedAgronomicGuide)
                .filter(
                    ApprovedAgronomicGuide.crop_name == g["crop_name"],
                    ApprovedAgronomicGuide.category == g["category"],
                )
                .first()
            )
            if existing:
                continue

            guide = ApprovedAgronomicGuide(
                crop_name=g["crop_name"],
                category=g["category"],
                stage_name=g.get("stage_name"),
                icar_recommendation=g["icar_recommendation"],
                citation_source=g["citation_source"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(guide)
            inserted += 1

        db.commit()
        logger.info("Seeded %d ICAR agronomic guidance cards.", inserted)
        return db.query(ApprovedAgronomicGuide).count()

    @classmethod
    def retrieve_guidance(
        cls,
        db: Session,
        crop_name: str,
        category: Optional[str] = None,
        stage_name: Optional[str] = None,
    ) -> list[ApprovedAgronomicGuide]:
        """Fetch matching verified ICAR package of practices cards."""
        query = db.query(ApprovedAgronomicGuide).filter(ApprovedAgronomicGuide.crop_name.ilike(crop_name))
        if category:
            query = query.filter(ApprovedAgronomicGuide.category == category.upper().strip())
        if stage_name:
            query = query.filter(
                (ApprovedAgronomicGuide.stage_name == stage_name.upper().strip())
                | (ApprovedAgronomicGuide.stage_name == None)
            )
        return query.all()

    @classmethod
    def build_rag_context_prompt(
        cls,
        db: Session,
        crop_name: str,
        current_stage: Optional[str] = None,
    ) -> str:
        """Construct grounded prompt snippet with verified ICAR sources."""
        cards = cls.retrieve_guidance(db, crop_name=crop_name, stage_name=current_stage)
        if not cards:
            return ""

        lines = [f"--- VERIFIED ICAR / SAU GUIDELINES FOR {crop_name.upper()} ---"]
        for card in cards:
            lines.append(f"[{card.category}] {card.icar_recommendation}")
            lines.append(f"Citation Source: {card.citation_source}")
        lines.append("--- END OF VERIFIED GUIDELINES ---")
        return "\n".join(lines)

