# 🔍 Krishi Mitra / AgriNova — Backend Gap Analysis & Discrepancy Register

**Author**: Senior Backend Architect & Systems Auditor  
**Date**: October 30, 2026  
**Repository**: `https://github.com/EvaChaudhari/AgriNova.git`  
**Active Branch**: `feature/backend-core`  
**Git HEAD**: `fe97199`  

---

## 1. Executive Summary & Verification Methodology

A comprehensive audit of the AgriNova backend was conducted against the target architecture set forth in the master prompt and existing documentation. Every existing file, database table, API route, mathematical engine, and test script was verified through direct code inspection and test execution.

### Verification Baseline
- **Environment**: macOS, Python 3.12.14, FastAPI 0.162.0, SQLAlchemy 2.1.6, GeoAlchemy2 0.20.0, Shapely 2.2.0, Alembic 1.20.1, Pytest 9.2.0.
- **Existing Tests**: 23 test cases in `backend/tests/` executed via `PYTHONPATH=backend .venv/bin/pytest -v`.
- **Test Results**: **23 passed** in 0.58s (0 failures, 1 warning regarding `httpx` deprecation in `starlette.testclient`).

---

## 2. Discrepancy Register

This register identifies explicit divergences between:
1. **Target Architecture (Master Prompt)**
2. **Repository README (`README.md`)**
3. **Previous Architectural Progress Report (`krishi_mitra_backend_report.md`)**
4. **Actual Repository Checkout (`HEAD`)**

| # | Topic | Documentation / Target Claim | Actual Code Reality | Severity | Risk & Impact |
|---|---|---|---|---|---|
| **D-01** | **Identity & Authentication** | Target mandates multi-tenant authentication with `User`, `FarmerProfile`, `Device`, `ConsentRecord`, token handling, and cross-farmer authorization checks. | Implemented as strictly single-tenant hardware identifier (`device_id` string). No passwords, JWTs, OAuth2, or sessions. Anyone presenting `device_id` has full access to the plot. | **CRITICAL** | Zero cryptographic auth. Any malicious client guessing or sniffing a `device_id` can read or overwrite plots and chat sessions. |
| **D-02** | **Consent Management** | Target S16 & M03 mandate consent tracking, consent withdrawal, audit logs, and data governance. | `ConsentRecord` and `AuditLog` models/tables do not exist in the codebase. | **HIGH** | Violates Indian Digital Personal Data Protection (DPDP) Act 2023 requirements for agricultural data platforms. |
| **D-03** | **Health & Readiness Endpoints** | Target M00 requires distinct `GET /health` and `GET /ready` endpoints where health and readiness are distinguishable. | **RESOLVED IN MILESTONE A**: `GET /health` (liveness without DB) and `GET /ready` (readiness with real `SELECT 1` DB ping and storage canary) implemented and verified in `main.py` and `test_foundation.py`. | **RESOLVED** | Distinguishable process health and subsystem dependencies. |
| **D-04** | **Database Schema Scope** | Target architecture defines 29 logical entities (Farms, WeatherObservations, WaterSources, SatelliteScenes, Crops, Checkpoints, etc.). | Only 7 physical tables exist: `device_profiles`, `farm_plots`, `crop_cycles`, `groundwater_observations`, `soil_health_records`, `chat_sessions`, `chat_messages`. | **HIGH** | Observations (weather, satellite, crops) are ephemeral in memory during context assembly rather than persisted historically. |
| **D-05** | **Multi-Plot & Farm Hierarchy** | Target M04 mandates `Farm` holding multiple `FarmPlot` records. | `FarmPlot` is linked directly to `device_id`. In `plots.py`, registering a new plot sets all prior plots to `is_active = False` (soft single-active-plot restriction). | **MEDIUM** | Farmers cannot manage multiple active fragmented parcels simultaneously. |
| **D-06** | **Scientific Knowledge Retrieval (RAG)** | Target S11 mandates document ingestion, chunking, search, ICAR citations, and guardrails. | Chat receptor uses hardcoded system prompt instructions and deterministic string templates. No vector store, pgvector, or document retrieval pipeline exists. | **HIGH** | Agricultural answers rely on either external Gemini generation or a static fallback dictionary. |
| **D-07** | **Offline Sync Protocol** | Target S13 mandates push/pull synchronization with idempotency keys, conflict resolution, and change logs. | No sync endpoints or sync tables exist. All API operations expect live synchronous HTTP connection. | **HIGH** | Rural smallholders with intermittent 2G/4G connectivity cannot queue actions offline. |
| **D-08** | **Crop Planner & Roadmaps** | Target S13 mandates crop suitability ranking, calendar schedules, and checkpoint reminders. | Not implemented. Crop cycles are stored statically with sowing and harvest dates, but no dynamic roadmaps or checkpoint progression exists. | **MEDIUM** | Farmer cannot explore seasonal crop options or track milestone-based growth interventions. |
| **D-09** | **Notifications System** | Target S13 mandates hazard alerts, irrigation reminders, read/unread states, and notification preferences. | Not implemented. Alerts are only returned inline in the bootstrap payload or chat response. | **MEDIUM** | Proactive hazard warnings cannot be pushed to farmers asynchronously. |
| **D-10** | **Satellite STAC Ingestion** | Target S5 mandates raster download, cloud masking, clipping, and NDVI calculation via Rasterio/NumPy. | `satellite_stac.py` searches AWS Earth Search STAC items, extracts scene cloud cover metadata, and returns synthetic sigmoid index estimates. Actual raster assets (COG TIFFs) are neither downloaded nor clipped. | **MEDIUM** | Real satellite spectral band calculations do not run on live raster arrays; synthetic curve is substituted. |

---

## 3. Detailed Gap Analysis by Architectural Domain

### 3.1 Application Foundation & Configuration (M00)
- **What Works**: FastAPI boots cleanly with lifespan context; Pydantic Settings reads `.env`; CORS middleware configured; SQLAlchemy engine supports both SQLite and PostgreSQL.
- **What is Missing**:
  - `GET /health` (liveness probe verifying process) and `GET /ready` (readiness probe verifying database connectivity via `SELECT 1` and storage availability).
  - Centralized exception handlers for `SQLAlchemyError`, `ValidationError`, and domain-specific agricultural exceptions (`HydrologicalComputationError`, `HazardStateViolation`).
  - Structured JSON logging with trace correlation IDs.

### 3.2 Shared Contracts & Schemas (M01)
- **What Works**: Pydantic v2 schemas for `DeviceProfile`, `PlotCreateRequest`, `PlotResponse`, `CropCycle`, `ChatReceptorResponse`.
- **What is Missing**:
  - Standardized observation metadata envelope (`unit`, `source`, `observation_timestamp`, `retrieval_timestamp`, `quality_flag`, `uncertainty`).
  - Standardized paginated API list responses (`total`, `page`, `limit`, `items`).
  - Standardized RFC 7807 problem details error schemas.

### 3.3 Database & Storage Layer (M02)
- **What Works**: SQLAlchemy declarative models; `PostGISGeometry` TypeDecorator handles native PostGIS in PostgreSQL and WKT text in SQLite; Alembic migration `f49b0e3b4438` applies cleanly.
- **What is Missing**:
  - Dedicated Repository layer (current API handlers execute raw `db.query(...)` directly).
  - Spatial indexes (`GIST`) for PostgreSQL in production (currently indexes are standard B-tree).
  - Object storage abstraction (S3 / MinIO) for large audio files, leaf photos, and satellite rasters (currently stored in local storage or in-memory).

### 3.4 Identity, Consent, and Farmer Registry (M03, M04, S1)
- **What Works**: Device profile creation and lookup; GeoJSON polygon parsing, WGS84 geodesic area calculation in hectares using latitude-calibrated metric scaling; centroid calculation; crop cycle registration.
- **What is Missing**:
  - JWT / API token issuance and verification.
  - Consent tracking model (`ConsentRecord`) tracking purpose (`IRRIGATION_ADVISORY`, `SOIL_MAPPING`, `THIRD_PARTY_SHARING`), grant date, and revocation state.
  - Farmer entity separated from hardware Device entity (allowing a farmer to change phones without losing farm history).
  - Farm entity grouping multiple plots.

### 3.5 Data Platform Ingestion & Services (S0, S2, S3, S4, S5, S6, S7)
- **Reference Geography (S0)**: Baseline dictionary in `fallback_data.py` has CGWB district entries for Telangana, Maharashtra, AP, Karnataka, and Punjab. Missing: formal administrative boundary hierarchy (`State` -> `District` -> `Block` -> `Village` -> `AgroClimaticZone`).
- **Soil (S2)**: SoilHealthRecord table exists; fallback benchmarks for 5 soil types (Vertisol, Alfisol, Inceptisol, Sandy Loam, Clay Loam). Missing: automated Soil Health Card API ingestion client and lab test certificate attachment.
- **Weather (S3)**: OpenWeatherMap live client and IMD monthly agro-climatic normal fallback. Missing: multi-day forecast modeling, historical rainfall accumulation tracking, provider retry policies with exponential backoff.
- **Water Resources (S4)**: Groundwater observation model with depth in mbgl. Missing: surface water body tracking, canal roster schedules, and India-WRIS automated scraping/API adapter.
- **Satellite (S5)**: STAC API query payload constructed for Sentinel-2 L2A; synthetic sigmoid phenology fallback based on Days After Sowing (DAS). Missing: COG asset pixel reading, raster clipping to farm polygon using Rasterio/NumPy, cloud pixel masking.
- **Terrain & Hydrology (S6)**: Plot model contains `elevation_m` and `slope_percent` fields. Missing: automated DEM (SRTM / Copernicus 30m) raster query by centroid to derive elevation, slope, and aspect automatically.
- **Crop Knowledge Base (S7)**: Hardcoded dictionary in `fallback_data.py` covering Cotton, Paddy/Rice, Maize, Soybean, Wheat, Groundnut, Chana with FAO-56 Kc, root depths, and growth stages. Missing: database-backed versioned crop knowledge repository with agronomic reference citations.

### 3.6 Agricultural Intelligence Engines (S8, S9, S10)
- **FAO-56 Hydrology (S8)**:
  - *Status*: **SCIENTIFICALLY EVALUATED** against standard FAO-56 equations. Penman-Monteith ET0, TAW, RAW, depletion, and effective rainfall run deterministically.
  - *Gaps*: Soil moisture sensor telemetry ingestion; multi-day predictive water depletion projections.
- **Extreme Weather Hazard State Machine (S10)**:
  - *Status*: **FUNCTIONALLY INTEGRATED**. Evaluates priority FSM (STORM_FLOOD_MODE -> EL_NINO_DROUGHT_MODE -> NORMAL_MODE). Triggers chemical spraying halt, topsoil erosion risk, and root asphyxiation alerts.
  - *Gaps*: Configurable dynamic threshold overrides; historical hazard event logging table (`hazard_events`).
- **Crop Health & Yield Estimation (S9)**:
  - *Status*: **PARTIALLY IMPLEMENTED**. Leaf vision service diagnoses Pink Bollworm, Fall Armyworm, and Yellow Rust with CIB&RC IPM guidelines.
  - *Gaps*: Quantitative vegetative vigor comparison against historical baseline; multi-spectral water stress indices; empirical yield estimation modeling.

### 3.7 AI Advisory, Retrieval, and Multilingual Voice (S11, S12)
- **Multilingual Speech (S12)**:
  - *Status*: **FUNCTIONALLY INTEGRATED**. Bhashini ULCA STT/TTS adapter with offline synthetic PCM 16-bit WAV fallback supporting Hindi, Telugu, Marathi, and English.
- **Gemini Chat Integration (S12)**:
  - *Status*: **FUNCTIONALLY INTEGRATED**. Connects to Gemini 2.5 Flash via REST with ICAR Senior Scientist system prompt and full agricultural context injection. When API key is unset, switches to deterministic multilingual response templates.
- **Approved Knowledge Retrieval (S11)**:
  - *Status*: **NOT IMPLEMENTED**. Missing searchable repository of vetted ICAR packages of practices (PoP).

### 3.8 Farmer Workflows (S13)
- **Crop Planner**: Not implemented.
- **Crop Roadmap & Checkpoints**: Not implemented.
- **Offline Synchronization**: Not implemented.
- **Farmer Notifications**: Not implemented.

---

## 4. Current State Categorization

| Category | Components |
|---|---|
| **What Works Cleanly** | • FastAPI application lifecycle and SQLite/PostGIS connectivity.<br>• FAO-56 Penman-Monteith ET0, TAW, RAW, and soil water balance depletion calculation.<br>• Extreme weather hazard state machine (STORM_FLOOD_MODE chemical halting & EL_NINO drought mode).<br>• GeoJSON field polygon registration with geodesic centroid & hectare area calculation.<br>• Unified chat receptor accepting text, voice audio, and leaf pathology images.<br>• Bhashini STT/TTS adapter and deterministic offline WAV generation.<br>• CIB&RC IPM leaf vision validator.<br>• Regional fallback baselines (CGWB water tables, IMD normals, soil profiles).<br>• 23 passing unit and integration tests. |
| **What Partially Works** | • Satellite STAC client (retrieves scene metadata, but substitutes synthetic curve rather than raster clipping).<br>• Context builder (assembles live packet in-memory, but does not persist historical observations).<br>• Weather service (fetches current weather, but lacks multi-day forecast storage and rolling accumulation). |
| **What is Missing** | • Formal Authentication & Authorization (JWT tokens, farmer login).<br>• Consent Management & Audit Logging (`ConsentRecord`, `AuditLog`).<br>• Distinct `GET /health` and `GET /ready` endpoints.<br>• Persistent observations schema (Weather, Satellite, Crop Knowledge).<br>• Crop Planner & Roadmap Checkpoint workflows.<br>• Offline Synchronization engine.<br>• Proactive Notification system.<br>• Document Retrieval / RAG for ICAR guidelines. |
| **What is Broken** | • No breaking test failures (23/23 pass).<br>• Single-active-plot constraint in `plots.py` silences previous plots when a new one is added.<br>• Missing `/health` and `/ready` standard probe routes. |
| **External Credentials Required** | • `GEMINI_API_KEY`: Required for live multimodal LLM inference (currently operating in deterministic fallback).<br>• `BHASHINI_API_KEY` & `BHASHINI_USER_ID`: Required for live Indian language STT/TTS.<br>• `OPENWEATHERMAP_API_KEY`: Required for live weather observations. |
| **Datasets / Licences Needed** | • ICAR Packages of Practices (PoP) documents (for knowledge retrieval).<br>• SRTM / Copernicus 30m Global DEM raster access.<br>• Survey of India / LGD (Local Government Directory) village and block administrative codes. |
| **Agricultural Validation Needed** | • Regional calibration of FAO-56 depletion fractions ($p$) under severe Vertisol cracking.<br>• Expert review of kaolin clay anti-transpirant concentration recommendations.<br>• Validation of local soil texture hydraulic parameters against ICAR-NBSS&LUP soil maps. |

---

## 5. Recommended Implementation Roadmap

To maintain stability while expanding functionality, we will follow the phased milestones:

1. **Milestone A (Foundation & Observability)**:
   - Add distinguishable `GET /health` and `GET /ready` probes with DB check.
   - Standardize error handling and exception models.
   - Introduce structured logging.
2. **Milestone B (Identity, Consent & Multi-Plot)**:
   - Introduce `User`, `FarmerProfile`, `Device`, `ConsentRecord`, and `AuditLog` models.
   - Implement JWT authentication with backward compatibility for device UUID.
   - Support multiple active plots per farmer.
3. **Milestone C (Data Platform & Repositories)**:
   - Implement Repository layer for clean separation of database access.
   - Add historical observation persistence for weather, soil, and satellite.
   - Implement DEM elevation and slope auto-lookup.
4. **Milestone D (Knowledge Base & Agricultural Intelligence)**:
   - Database-backed crop knowledge base.
   - Multi-day predictive water balance projections.
5. **Milestone E (Farmer Workflows)**:
   - Crop suitability planner.
   - Crop-cycle milestone roadmap.
   - Offline sync and notifications.

