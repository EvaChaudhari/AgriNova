"""Agronomic Knowledge Ingestion & Database Seed Service.

Seeds production-grade agronomic taxonomy, cultivar varieties, FAO-56 growth stages,
ICAR STCR nutrient benchmarks, and CIB&RC IPM pest profiles for 8 staple Indian crops.
Ensures strictly idempotent execution.
"""

import logging
from sqlalchemy.orm import Session

from app.models.crop_knowledge import (
    Crop,
    CropGrowthStage,
    CropNutrientBenchmark,
    CropPestProfile,
    CropVariety,
)

logger = logging.getLogger("agrinova.crop_seed")

CROPS_SEED_DATA = [
    {
        "name": "Cotton",
        "scientific_name": "Gossypium hirsutum",
        "season": "KHARIF",
        "category": "FIBRE",
        "standard_duration_days": 160,
        "varieties": [
            {"variety_name": "Bt Cotton RCH-2", "duration_days": 155, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 28.0},
            {"variety_name": "DCH-32 Hybrid", "duration_days": 165, "drought_tolerance": "MEDIUM", "flood_tolerance": "LOW", "potential_yield_q_ha": 25.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 25, "kc": 0.35, "rooting_depth_m": 0.30, "depletion_fraction_p": 0.65, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 26, "end_das": 60, "kc": 0.75, "rooting_depth_m": 0.70, "depletion_fraction_p": 0.65, "ky": 0.70, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 61, "end_das": 105, "kc": 1.20, "rooting_depth_m": 1.10, "depletion_fraction_p": 0.65, "ky": 1.20, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 106, "end_das": 160, "kc": 0.65, "rooting_depth_m": 1.20, "depletion_fraction_p": 0.70, "ky": 0.50, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 4.40, "stcr_b_n": 0.38,
            "stcr_a_p": 1.80, "stcr_b_p": 0.45,
            "stcr_a_k": 2.10, "stcr_b_k": 0.18,
            "max_n_kg_ha": 150.0, "max_p_kg_ha": 75.0, "max_k_kg_ha": 75.0,
            "target_yield_default_q_ha": 25.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Pink Bollworm (Pectinophora gossypiella)",
                "pest_type": "INSECT",
                "affected_growth_stage": "FLOWERING",
                "symptoms": "Rosetted flowers, young bolls with entrance holes plugged with excreta, premature boll dropping.",
                "economic_threshold_etl": "8 moths/trap/night for 3 consecutive nights or 10% damaged green bolls.",
                "ipm_practice": "Install pheromone traps @ 5/ha; release Trichogramma chilonis egg parasitoid @ 150000/ha; spray Neem Seed Kernel Extract (NSKE 5%).",
                "approved_chemical": "Chlorantraniliprole 18.5% SC @ 150 ml/ha",
                "cib_restriction": "Do not spray during full bloom to preserve natural pollinators.",
            },
            {
                "pest_name": "Whitefly (Bemisia tabaci)",
                "pest_type": "INSECT",
                "affected_growth_stage": "VEGETATIVE",
                "symptoms": "Yellowing and upward curling of leaves, honeydew excretion causing sooty mold, vector for Cotton Leaf Curl Virus.",
                "economic_threshold_etl": "6-8 adults per leaf before 9 AM.",
                "ipm_practice": "Erect yellow sticky traps @ 25/ha; avoid excessive urea top-dressing which induces succulent vegetative flush.",
                "approved_chemical": "Diafenthiuron 50% WP @ 600 g/ha",
                "cib_restriction": "Alternate chemical mode of action to avoid neonicotinoid resistance.",
            },
        ],
    },
    {
        "name": "Paddy",
        "scientific_name": "Oryza sativa",
        "season": "KHARIF",
        "category": "CEREAL",
        "standard_duration_days": 125,
        "varieties": [
            {"variety_name": "BPT-5204 (Samba Mahsuri)", "duration_days": 140, "drought_tolerance": "LOW", "flood_tolerance": "HIGH", "potential_yield_q_ha": 55.0},
            {"variety_name": "IR-64", "duration_days": 120, "drought_tolerance": "LOW", "flood_tolerance": "MEDIUM", "potential_yield_q_ha": 50.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 1.05, "rooting_depth_m": 0.20, "depletion_fraction_p": 0.20, "ky": 0.60, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 50, "kc": 1.15, "rooting_depth_m": 0.45, "depletion_fraction_p": 0.20, "ky": 0.80, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 51, "end_das": 90, "kc": 1.25, "rooting_depth_m": 0.60, "depletion_fraction_p": 0.20, "ky": 1.30, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 91, "end_das": 125, "kc": 0.95, "rooting_depth_m": 0.60, "depletion_fraction_p": 0.30, "ky": 0.50, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 4.25, "stcr_b_n": 0.45,
            "stcr_a_p": 2.15, "stcr_b_p": 0.65,
            "stcr_a_k": 2.45, "stcr_b_k": 0.25,
            "max_n_kg_ha": 150.0, "max_p_kg_ha": 60.0, "max_k_kg_ha": 60.0,
            "target_yield_default_q_ha": 50.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Brown Planthopper (Nilaparvata lugens)",
                "pest_type": "INSECT",
                "affected_growth_stage": "FLOWERING",
                "symptoms": "Hopper burn: circular patches of drying plants turning brown in the field, plants drying out from base.",
                "economic_threshold_etl": "5-10 hoppers per hill.",
                "ipm_practice": "Practice alternate wetting and drying (AWD) irrigation; avoid excessive nitrogen fertilizer.",
                "approved_chemical": "Trifflumezopyrim 10% SC @ 235 ml/ha",
                "cib_restriction": "Ensure spray nozzle reaches basal stem area where hoppers feed.",
            },
        ],
    },
    {
        "name": "Wheat",
        "scientific_name": "Triticum aestivum",
        "season": "RABI",
        "category": "CEREAL",
        "standard_duration_days": 120,
        "varieties": [
            {"variety_name": "HD-2967", "duration_days": 130, "drought_tolerance": "MEDIUM", "flood_tolerance": "LOW", "potential_yield_q_ha": 52.0},
            {"variety_name": "PBW-550", "duration_days": 120, "drought_tolerance": "LOW", "flood_tolerance": "LOW", "potential_yield_q_ha": 48.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 0.30, "rooting_depth_m": 0.25, "depletion_fraction_p": 0.55, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 55, "kc": 0.75, "rooting_depth_m": 0.75, "depletion_fraction_p": 0.55, "ky": 0.60, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 56, "end_das": 95, "kc": 1.15, "rooting_depth_m": 1.05, "depletion_fraction_p": 0.55, "ky": 1.15, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 96, "end_das": 120, "kc": 0.40, "rooting_depth_m": 1.10, "depletion_fraction_p": 0.65, "ky": 0.40, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 4.50, "stcr_b_n": 0.42,
            "stcr_a_p": 2.80, "stcr_b_p": 0.60,
            "stcr_a_k": 2.90, "stcr_b_k": 0.18,
            "max_n_kg_ha": 150.0, "max_p_kg_ha": 60.0, "max_k_kg_ha": 50.0,
            "target_yield_default_q_ha": 48.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Yellow Rust (Puccinia striiformis)",
                "pest_type": "FUNGUS",
                "affected_growth_stage": "VEGETATIVE",
                "symptoms": "Yellow pustules arranged in linear stripes on leaf blades, powdery yellow spores.",
                "economic_threshold_etl": "Appearance of first active rust pustules in the field.",
                "ipm_practice": "Plant resistant cultivars; avoid late sowing.",
                "approved_chemical": "Propiconazole 25% EC @ 500 ml/ha",
                "cib_restriction": "Spray immediately upon first symptom detection in cool, humid weather.",
            },
        ],
    },
    {
        "name": "Soybean",
        "scientific_name": "Glycine max",
        "season": "KHARIF",
        "category": "OILSEED",
        "standard_duration_days": 100,
        "varieties": [
            {"variety_name": "JS-335", "duration_days": 95, "drought_tolerance": "MEDIUM", "flood_tolerance": "LOW", "potential_yield_q_ha": 22.0},
            {"variety_name": "JS-9560", "duration_days": 90, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 20.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 0.40, "rooting_depth_m": 0.25, "depletion_fraction_p": 0.50, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 45, "kc": 0.80, "rooting_depth_m": 0.65, "depletion_fraction_p": 0.50, "ky": 0.60, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 46, "end_das": 75, "kc": 1.15, "rooting_depth_m": 0.90, "depletion_fraction_p": 0.50, "ky": 1.10, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 76, "end_das": 100, "kc": 0.50, "rooting_depth_m": 0.90, "depletion_fraction_p": 0.60, "ky": 0.40, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 5.20, "stcr_b_n": 0.25,
            "stcr_a_p": 2.40, "stcr_b_p": 0.45,
            "stcr_a_k": 3.10, "stcr_b_k": 0.15,
            "max_n_kg_ha": 40.0,  # Legume fixes atmospheric N
            "max_p_kg_ha": 70.0, "max_k_kg_ha": 40.0,
            "target_yield_default_q_ha": 20.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Girdle Beetle (Obereopsis brevis)",
                "pest_type": "INSECT",
                "affected_growth_stage": "VEGETATIVE",
                "symptoms": "Ring-shaped girdling on petiole/stem causing drooping and drying of upper leaves.",
                "economic_threshold_etl": "5 damaged plants per meter row length.",
                "ipm_practice": "Collect and destroy girdled plant parts during early infestation.",
                "approved_chemical": "Thiamethoxam 12.6% + Lambda-cyhalothrin 9.5% ZC @ 125 ml/ha",
                "cib_restriction": "Ensure proper PPE during spraying.",
            },
        ],
    },
    {
        "name": "Maize",
        "scientific_name": "Zea mays",
        "season": "KHARIF",
        "category": "CEREAL",
        "standard_duration_days": 110,
        "varieties": [
            {"variety_name": "DHM-117", "duration_days": 105, "drought_tolerance": "MEDIUM", "flood_tolerance": "LOW", "potential_yield_q_ha": 65.0},
            {"variety_name": "Pioneer P3396", "duration_days": 115, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 70.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 0.30, "rooting_depth_m": 0.25, "depletion_fraction_p": 0.55, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 50, "kc": 0.70, "rooting_depth_m": 0.70, "depletion_fraction_p": 0.55, "ky": 0.70, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 51, "end_das": 85, "kc": 1.20, "rooting_depth_m": 1.00, "depletion_fraction_p": 0.55, "ky": 1.25, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 86, "end_das": 110, "kc": 0.50, "rooting_depth_m": 1.00, "depletion_fraction_p": 0.65, "ky": 0.40, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 3.80, "stcr_b_n": 0.40,
            "stcr_a_p": 2.20, "stcr_b_p": 0.50,
            "stcr_a_k": 2.80, "stcr_b_k": 0.20,
            "max_n_kg_ha": 180.0, "max_p_kg_ha": 80.0, "max_k_kg_ha": 60.0,
            "target_yield_default_q_ha": 55.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Fall Armyworm (Spodoptera frugiperda)",
                "pest_type": "INSECT",
                "affected_growth_stage": "VEGETATIVE",
                "symptoms": "Pinholes in whorl leaves, extensive window pane feeding, sawdust-like fecal matter inside whorl.",
                "economic_threshold_etl": "5% infested whorls at seedling stage or 10% at mid-whorl stage.",
                "ipm_practice": "Apply Metarhizium anisopliae or Bacillus thuringiensis (Bt) @ 2g/L; hand-pick egg masses.",
                "approved_chemical": "Emamectin Benzoate 5% SG @ 200 g/ha",
                "cib_restriction": "Direct spray jet straight into the central whorl cylinder.",
            },
        ],
    },
    {
        "name": "Chickpea",
        "scientific_name": "Cicer arietinum",
        "season": "RABI",
        "category": "PULSE",
        "standard_duration_days": 110,
        "varieties": [
            {"variety_name": "JG-11", "duration_days": 105, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 20.0},
            {"variety_name": "JAKI-9218", "duration_days": 110, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 22.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 0.40, "rooting_depth_m": 0.20, "depletion_fraction_p": 0.50, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 45, "kc": 0.70, "rooting_depth_m": 0.55, "depletion_fraction_p": 0.50, "ky": 0.60, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 46, "end_das": 80, "kc": 1.05, "rooting_depth_m": 0.75, "depletion_fraction_p": 0.50, "ky": 1.00, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 81, "end_das": 110, "kc": 0.45, "rooting_depth_m": 0.75, "depletion_fraction_p": 0.60, "ky": 0.40, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 3.50, "stcr_b_n": 0.20,
            "stcr_a_p": 2.60, "stcr_b_p": 0.40,
            "stcr_a_k": 2.80, "stcr_b_k": 0.15,
            "max_n_kg_ha": 30.0, "max_p_kg_ha": 60.0, "max_k_kg_ha": 30.0,
            "target_yield_default_q_ha": 18.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Gram Pod Borer (Helicoverpa armigera)",
                "pest_type": "INSECT",
                "affected_growth_stage": "FLOWERING",
                "symptoms": "Defoliation of tender leaves, round holes bored into developing pods with head inside.",
                "economic_threshold_etl": "1 larva per meter row or 1 moth/trap/day.",
                "ipm_practice": "Install bird perches @ 40/ha; plant African Marigold border crop; spray HaNPV @ 250 LE/ha.",
                "approved_chemical": "Chlorantraniliprole 18.5% SC @ 125 ml/ha",
                "cib_restriction": "Do not exceed recommended concentration to avoid residue in grain.",
            },
        ],
    },
    {
        "name": "Mustard",
        "scientific_name": "Brassica juncea",
        "season": "RABI",
        "category": "OILSEED",
        "standard_duration_days": 125,
        "varieties": [
            {"variety_name": "Pusa Bold", "duration_days": 120, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 22.0},
            {"variety_name": "RH-749", "duration_days": 130, "drought_tolerance": "HIGH", "flood_tolerance": "LOW", "potential_yield_q_ha": 25.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 20, "kc": 0.35, "rooting_depth_m": 0.25, "depletion_fraction_p": 0.50, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 21, "end_das": 50, "kc": 0.75, "rooting_depth_m": 0.65, "depletion_fraction_p": 0.50, "ky": 0.65, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 51, "end_das": 85, "kc": 1.15, "rooting_depth_m": 0.95, "depletion_fraction_p": 0.50, "ky": 1.10, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 86, "end_das": 125, "kc": 0.45, "rooting_depth_m": 1.00, "depletion_fraction_p": 0.60, "ky": 0.40, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 4.80, "stcr_b_n": 0.35,
            "stcr_a_p": 2.50, "stcr_b_p": 0.55,
            "stcr_a_k": 3.00, "stcr_b_k": 0.20,
            "max_n_kg_ha": 100.0, "max_p_kg_ha": 50.0, "max_k_kg_ha": 40.0,
            "target_yield_default_q_ha": 20.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Mustard Aphid (Lipaphis erysimi)",
                "pest_type": "INSECT",
                "affected_growth_stage": "FLOWERING",
                "symptoms": "Curling and crinkling of inflorescence, stunted pods, glistening honeydew on flowers.",
                "economic_threshold_etl": "20-25 aphids per 10 cm central twig.",
                "ipm_practice": "Early sowing before October 15; conserve Coccinellid predatory beetles.",
                "approved_chemical": "Dimethoate 30% EC @ 650 ml/ha",
                "cib_restriction": "Cease spraying 2 weeks before grain harvest.",
            },
        ],
    },
    {
        "name": "Sugarcane",
        "scientific_name": "Saccharum officinarum",
        "season": "KHARIF",
        "category": "CASH",
        "standard_duration_days": 360,
        "varieties": [
            {"variety_name": "Co-0238 (Karan 4)", "duration_days": 350, "drought_tolerance": "MEDIUM", "flood_tolerance": "HIGH", "potential_yield_q_ha": 950.0},
            {"variety_name": "Co-86032 (Nayana)", "duration_days": 365, "drought_tolerance": "HIGH", "flood_tolerance": "MEDIUM", "potential_yield_q_ha": 1050.0},
        ],
        "growth_stages": [
            {"stage_name": "INITIAL", "start_das": 0, "end_das": 45, "kc": 0.40, "rooting_depth_m": 0.30, "depletion_fraction_p": 0.65, "ky": 0.40, "critical_water_stage": False},
            {"stage_name": "VEGETATIVE", "start_das": 46, "end_das": 180, "kc": 0.85, "rooting_depth_m": 0.85, "depletion_fraction_p": 0.65, "ky": 0.80, "critical_water_stage": False},
            {"stage_name": "FLOWERING", "start_das": 181, "end_das": 280, "kc": 1.25, "rooting_depth_m": 1.20, "depletion_fraction_p": 0.65, "ky": 1.20, "critical_water_stage": True},
            {"stage_name": "MATURITY", "start_das": 281, "end_das": 360, "kc": 0.75, "rooting_depth_m": 1.20, "depletion_fraction_p": 0.70, "ky": 0.50, "critical_water_stage": False},
        ],
        "stcr_benchmark": {
            "stcr_a_n": 0.28, "stcr_b_n": 0.30,
            "stcr_a_p": 0.15, "stcr_b_p": 0.40,
            "stcr_a_k": 0.25, "stcr_b_k": 0.15,
            "max_n_kg_ha": 250.0, "max_p_kg_ha": 100.0, "max_k_kg_ha": 120.0,
            "target_yield_default_q_ha": 850.0,
        },
        "pest_profiles": [
            {
                "pest_name": "Early Shoot Borer (Chilo infuscatellus)",
                "pest_type": "INSECT",
                "affected_growth_stage": "INITIAL",
                "symptoms": "Dead hearts in young shoots which can be easily pulled out emitting an offensive odor.",
                "economic_threshold_etl": "15% dead hearts in the field.",
                "ipm_practice": "Trash mulching @ 3.5 t/ha at 3-5 days after planting; release Trichogramma chilonis.",
                "approved_chemical": "Chlorantraniliprole 0.4% G @ 18.75 kg/ha applied at soil furrow",
                "cib_restriction": "Apply along cane rows followed by light earthing up.",
            },
        ],
    },
]


def seed_crops_if_empty(db: Session) -> int:
    """Idempotently seed the 8 staple Indian crops into the database."""
    existing_count = db.query(Crop).count()
    if existing_count >= len(CROPS_SEED_DATA):
        return existing_count

    inserted_count = 0
    for crop_dict in CROPS_SEED_DATA:
        existing = db.query(Crop).filter(Crop.name == crop_dict["name"]).first()
        if existing:
            continue

        crop = Crop(
            name=crop_dict["name"],
            scientific_name=crop_dict["scientific_name"],
            season=crop_dict["season"],
            category=crop_dict["category"],
            standard_duration_days=crop_dict["standard_duration_days"],
            is_active=True,
        )
        db.add(crop)
        db.flush()  # Populates crop.id

        # Add varieties
        for var in crop_dict["varieties"]:
            variety = CropVariety(
                crop_id=crop.id,
                variety_name=var["variety_name"],
                duration_days=var["duration_days"],
                drought_tolerance=var["drought_tolerance"],
                flood_tolerance=var["flood_tolerance"],
                potential_yield_q_ha=var["potential_yield_q_ha"],
            )
            db.add(variety)

        # Add growth stages
        for stage in crop_dict["growth_stages"]:
            gs = CropGrowthStage(
                crop_id=crop.id,
                stage_name=stage["stage_name"],
                start_das=stage["start_das"],
                end_das=stage["end_das"],
                kc=stage["kc"],
                rooting_depth_m=stage["rooting_depth_m"],
                depletion_fraction_p=stage["depletion_fraction_p"],
                ky=stage["ky"],
                critical_water_stage=stage["critical_water_stage"],
            )
            db.add(gs)

        # Add STCR benchmark
        bm = crop_dict["stcr_benchmark"]
        stcr = CropNutrientBenchmark(
            crop_id=crop.id,
            stcr_a_n=bm["stcr_a_n"],
            stcr_b_n=bm["stcr_b_n"],
            stcr_a_p=bm["stcr_a_p"],
            stcr_b_p=bm["stcr_b_p"],
            stcr_a_k=bm["stcr_a_k"],
            stcr_b_k=bm["stcr_b_k"],
            max_n_kg_ha=bm["max_n_kg_ha"],
            max_p_kg_ha=bm["max_p_kg_ha"],
            max_k_kg_ha=bm["max_k_kg_ha"],
            target_yield_default_q_ha=bm["target_yield_default_q_ha"],
        )
        db.add(stcr)

        # Add pest profiles
        for pest in crop_dict["pest_profiles"]:
            pp = CropPestProfile(
                crop_id=crop.id,
                pest_name=pest["pest_name"],
                pest_type=pest["pest_type"],
                affected_growth_stage=pest["affected_growth_stage"],
                symptoms=pest["symptoms"],
                economic_threshold_etl=pest["economic_threshold_etl"],
                ipm_practice=pest["ipm_practice"],
                approved_chemical=pest.get("approved_chemical"),
                cib_restriction=pest.get("cib_restriction"),
            )
            db.add(pp)

        inserted_count += 1

    db.commit()
    logger.info("Agronomic knowledge seeded: %d new crops inserted.", inserted_count)
    return db.query(Crop).count()

