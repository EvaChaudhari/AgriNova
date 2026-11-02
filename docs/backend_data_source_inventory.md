# 🌐 Krishi Mitra / AgriNova — External Data Source & Ingestion Inventory

**Author**: Senior Backend Architect & Agricultural Data Systems Engineer  
**Audit Date**: October 30, 2026  

---

## 1. Architectural Ingestion Hierarchy

Krishi Mitra enforces a strict **3-tier data ingestion hierarchy** across all environmental dimensions:

$$\text{Tier 1: Physical IoT Telemetry} \longrightarrow \text{Tier 2: Public Government / External API} \longrightarrow \text{Tier 3: Regionally Calibrated Deterministic Fallback}$$

Every observation ingested or derived by the platform must be explicitly tagged with its **Provenance Quality Status**:
1. `MEASURED`: Directly recorded by physical in-situ sensor or certified laboratory testing.
2. `FORECAST`: Numerical meteorological simulation for future time steps.
3. `DERIVED`: Computed via deterministic physics models (e.g. FAO-56 $ET_0$).
4. `ESTIMATED`: Statistical or remote-sensing proxy.
5. `SYNTHETIC_FALLBACK`: Rule-based regional climatological baseline (never fabricated).

---

## 2. Comprehensive Data Source Catalog

### Layer 1: Weather & Meteorology
- **Provider**: OpenWeatherMap (Primary) / India Meteorological Department (IMD) Gridded Data.
- **Access Method**: REST API (`https://api.openweathermap.org/data/2.5/weather`).
- **Credentials Required**: `OPENWEATHERMAP_API_KEY` in `backend/.env`.
- **License / Terms**: OpenWeatherMap Free/Developer Tier; IMD open government data (National Data Sharing and Accessibility Policy - NDSAP).
- **Spatial Coverage & Resolution**: Point coordinates (latitude/longitude), approx. 1-2.5 km grid cell.
- **Temporal Coverage & Frequency**: Hourly updates, 24-hour rainfall forecast ($P_{24h}$).
- **Standardized Units**:
  - Temperature: Degrees Celsius (°C)
  - Relative Humidity: Percentage (%)
  - Wind Speed: Meters per second (m/s) at 2m height ($u_2$)
  - Solar Radiation: Megajoules per square meter per day (MJ/m²/day)
  - Rainfall: Millimeters (mm)
- **Known Limitations**: Cloud cover blocks optical solar sensors; free tier rate limits (60 calls/min); API timeouts during server maintenance.
- **Deterministic Regional Fallback**:
  - Module: [`services/fallback_data.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/services/fallback_data.py#L38) (`IMD_AGROCLIMATIC_NORMALS`).
  - Implementation: 12-month historical distribution table derived from 30-year IMD district normals across Indian agro-climatic zones.
  - Quality Flag Assigned: `SYNTHETIC_FALLBACK` (source: `AGRO_CLIMATIC_FALLBACK`).

---

### Layer 2: Groundwater & Water Table Depth
- **Provider**: Central Ground Water Board (CGWB) & India-WRIS (Water Resources Information System).
- **Access Method**:
  - Tier 1: Hardware IoT Telemetry via `POST /api/v1/plots/{id}/groundwater`.
  - Tier 2: India-WRIS automated REST API adapter (planned).
  - Tier 3: CGWB seasonal median lookup dictionary.
- **Credentials Required**: None for fallback; India-WRIS developer token when connected.
- **License / Terms**: Ministry of Jal Shakti, Government of India Open Data.
- **Spatial Coverage & Resolution**: District-level aquifer monitoring wells.
- **Temporal Coverage & Frequency**: Pre-monsoon (May) and Post-monsoon (November) seasonal campaigns.
- **Standardized Units**: Meters Below Ground Level (`mbgl`).
- **Known Limitations**: Observation well density is 1 well per 50-100 km²; regional medians do not reflect localized borewell drawdowns.
- **Deterministic Regional Fallback**:
  - Module: [`services/fallback_data.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/services/fallback_data.py#L11) (`CGWB_DISTRICT_GROUNDWATER_MBGL`).
  - Pre-calibrated Districts: Warangal (11.2 mbgl), Nalgonda (14.5 mbgl), Mahabubnagar (19.4 mbgl), Akola (12.6 mbgl), Ahmednagar (18.9 mbgl), Solapur (20.2 mbgl), Anantapur (22.4 mbgl), Ludhiana (21.0 mbgl).
  - National Default: 12.5 mbgl.
  - Quality Flag Assigned: `ESTIMATED` (source: `FALLBACK_DISTRICT`).

---

### Layer 3: Soil Physicochemical Properties
- **Provider**: Ministry of Agriculture & Farmers Welfare — Soil Health Card (SHC) Portal / ICAR-NBSS&LUP.
- **Access Method**:
  - Tier 1: Certified soil laboratory test via `POST /api/v1/plots/{id}/soil-health`.
  - Tier 2: Automated SHC API integration (planned).
  - Tier 3: Soil order benchmarks.
- **Credentials Required**: None for fallback; SHC API credentials for Tier 2.
- **License / Terms**: Government of India National Soil Health Card Scheme.
- **Spatial Coverage & Resolution**: 2.5 ha grid sampling (irrigated) / 10 ha (rainfed).
- **Temporal Coverage & Frequency**: Valid for 3-year soil testing cycle.
- **Standardized Units**:
  - Nitrogen: kg/ha
  - Phosphorus ($P_2O_5$): kg/ha
  - Potassium ($K_2O$): kg/ha
  - pH: Standard pH units [0 - 14]
  - Organic Carbon: Percentage (%)
  - Field Capacity ($\theta_{FC}$): Volumetric water content ($m^3/m^3$)
  - Permanent Wilting Point ($\theta_{WP}$): Volumetric water content ($m^3/m^3$)
- **Known Limitations**: Laboratory tests may be 1-2 years old; spatial variability across a single field.
- **Deterministic Regional Fallback**:
  - Module: [`services/fallback_data.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/services/fallback_data.py#L55) (`SOIL_TYPE_BENCHMARKS`).
  - Pre-calibrated Soil Orders:
    - `Vertisol` (Black Cotton): pH 7.8, N: 140 kg/ha, P: 18 kg/ha, K: 280 kg/ha, OC: 0.45%, $\theta_{FC}$: 0.40, $\theta_{WP}$: 0.22.
    - `Alfisol` (Red Sandy/Loam): pH 6.2, N: 160 kg/ha, P: 14 kg/ha, K: 180 kg/ha, OC: 0.35%, $\theta_{FC}$: 0.24, $\theta_{WP}$: 0.12.
    - `Inceptisol` (Alluvial): pH 7.2, N: 210 kg/ha, P: 22 kg/ha, K: 220 kg/ha, OC: 0.55%, $\theta_{FC}$: 0.32, $\theta_{WP}$: 0.16.
    - `Sandy Loam`: pH 6.8, N: 120 kg/ha, P: 12 kg/ha, K: 150 kg/ha, OC: 0.28%, $\theta_{FC}$: 0.18, $\theta_{WP}$: 0.08.
    - `Clay Loam`: pH 7.5, N: 175 kg/ha, P: 20 kg/ha, K: 240 kg/ha, OC: 0.50%, $\theta_{FC}$: 0.35, $\theta_{WP}$: 0.18.
  - Quality Flag Assigned: `SYNTHETIC_FALLBACK` (source: `REGIONAL_FALLBACK`).

---

### Layer 4: Satellite Multispectral Imagery
- **Provider**: European Space Agency (ESA) Copernicus Sentinel-2 L2A via AWS Earth Search STAC API.
- **Access Method**: STAC API POST search (`https://earth-search.aws.element84.com/v1/search`).
- **Credentials Required**: None (Open public STAC API hosted by Element84 / AWS Open Data).
- **License / Terms**: Creative Commons CC-BY 4.0 (Copernicus Open Access Policy).
- **Spatial Coverage & Resolution**: Global; 10m visible/NIR bands (B04, B08), 20m SWIR band (B11).
- **Temporal Coverage & Frequency**: 5-day revisit cycle.
- **Standardized Units**:
  - NDVI: Normalized Difference Vegetation Index $[-1.0, 1.0]$: $\frac{B08 - B04}{B08 + B04}$
  - NDWI: Normalized Difference Water Index (Gao 1996) $[-1.0, 1.0]$: $\frac{B08 - B11}{B08 + B11}$
  - Cloud Cover: Percentage (%)
- **Known Limitations**: Monsoon cloud cover during July-August frequently obscures optical scenes; STAC endpoints can experience latency.
- **Deterministic Regional Fallback**:
  - Module: [`engines/satellite_stac.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/engines/satellite_stac.py#L32) (`calculate_synthetic_indices`).
  - Sigmoid Phenological Curve: Calibrated by Days After Sowing (DAS) and crop growth stage ($INITIAL \implies VEGETATIVE \implies FLOWERING \implies MATURITY$).
  - Quality Flag Assigned: `SYNTHETIC_FALLBACK` (source: `SYNTHETIC_PHENOLOGY_MODEL`).

---

### Layer 5: Multilingual Speech Pipeline
- **Provider**: Bhashini ULCA (Ministry of Electronics and Information Technology - MeitY) / IndicWhisper & Indic-TTS.
- **Access Method**: REST API (`https://dhruva-api.bhashini.gov.in/services/inference/pipeline`).
- **Credentials Required**: `BHASHINI_API_KEY` and `BHASHINI_USER_ID` in `backend/.env`.
- **License / Terms**: Government of India National Language Translation Mission (NLTM) open APIs.
- **Supported Languages**: Hindi (`hi`), Telugu (`te`), Marathi (`mr`), English (`en`).
- **Standardized Formats**:
  - STT: PCM 16-bit WAV, 16kHz sampling rate.
  - TTS: Audio base64 Data URL (`data:audio/wav;base64,...`).
- **Known Limitations**: Vernacular agricultural dialects and noisy rural farm recordings can lower transcription accuracy.
- **Deterministic Offline Fallback**:
  - Module: [`services/speech_service.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/services/speech_service.py#L20) (`generate_fallback_wav`).
  - Synthesizes valid RFC-compliant PCM 16-bit mono 8kHz WAV byte streams instantly on the CPU with zero network dependency.

---

### Layer 6: Multimodal Vision & Plant Pathology
- **Provider**: Google Gemini 2.5 Flash Multimodal Vision API / Central Insecticides Board (CIB&RC) IPM Database.
- **Access Method**: REST API (`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`).
- **Credentials Required**: `GEMINI_API_KEY` in `backend/.env`.
- **License / Terms**: Google Cloud Developer terms; CIB&RC Directorate of Plant Protection, Quarantine & Storage guidelines.
- **Zero-Hallucination Policy**: Gemini prompt and fallback database forbid unverified chemical cocktails.
- **Deterministic Fallback Database**:
  - Module: [`services/vision_service.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/services/vision_service.py#L30) (`CIB_APPROVED_IPM_DATABASE`).
  - Evaluates Pink Bollworm (Cotton), Fall Armyworm (Maize), and Yellow Rust (Wheat) with specific IPM steps (5% NSKE, pheromone traps, Trichogramma) and CIB-registered chemical active ingredients with tank dosages (e.g. 4g Emamectin Benzoate 5% SG per 10L water).

---

## 3. Data Quality & Provenance Metadata Standards

Every data point returned to clients or passed between internal modules must include the standard provenance block:

```json
{
  "parameter": "reference_evapotranspiration",
  "value": 6.24,
  "unit": "mm/day",
  "provenance": {
    "source": "FAO56_PENMAN_MONTEITH",
    "quality_status": "DERIVED",
    "observation_timestamp": "2026-10-30T00:00:00Z",
    "retrieval_timestamp": "2026-10-30T23:20:00Z",
    "confidence_interval": 0.05,
    "fallback_used": false
  }
}
```

This guarantees full auditability, scientific traceability, and transparency for smallholder farmers.

