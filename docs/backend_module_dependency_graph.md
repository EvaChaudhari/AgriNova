# 🕸️ Krishi Mitra / AgriNova — Module Dependency Graph & Architecture Flow

**Author**: Senior Backend Architect  
**Audit Date**: October 30, 2026  

---

## 1. High-Level Modular Monolith Architecture

The Krishi Mitra backend is structured as a **Modular Monolith**. Modules communicate through explicitly typed Pydantic contracts and internal service interfaces. There are zero circular dependencies; the system forms a strict **Directed Acyclic Graph (DAG)**.

```mermaid
flowchart TD
    subgraph Foundation["Layer 0: Core Foundation & Infrastructure"]
        M00["M00: Core Config & Lifespan"]
        M01["M01: Shared Contracts & Schemas"]
        M02["M02: Database & Storage Engine"]
        S16["S16: Security & Access Control"]
    end

    subgraph IdentityLayer["Layer 1: Identity & Land Registry"]
        M03["M03: Identity, Auth & Consent"]
        M04["M04: Farm & Plot Registry"]
        S0["S0: Reference Geography"]
        S1["S1: Onboarding Orchestration"]
    end

    subgraph DataPlatform["Layer 2: Environmental Data Platform"]
        S2["S2: Soil Intelligence"]
        S3["S3: Weather & Climate"]
        S4["S4: Water Resources"]
        S5["S5: Satellite STAC & Phenology"]
        S6["S6: Terrain & DEM Analysis"]
        S7["S7: Crop Knowledge Base"]
    end

    subgraph Intelligence["Layer 3: Deterministic Scientific Engines"]
        S8["S8: FAO-56 Hydrology Engine"]
        S10["S10: Hazard State Machine (FSM)"]
        S9["S9: Leaf Pathology Vision & Yield"]
    end

    subgraph ContextAndAdvisory["Layer 4: AI Context & Multilingual Advisory"]
        CB["Context Builder Service"]
        S11["S11: Approved Knowledge Retrieval"]
        S12["S12: Grounded Gemini Gateway & Voice"]
    end

    subgraph Workflows["Layer 5: Farmer Workflows & Governance"]
        CP["Crop Suitability Planner"]
        RM["Milestone Roadmap & Checkpoints"]
        SYNC["Offline Data Sync Protocol"]
        NOTIF["Hazard & Irrigation Notifications"]
        S14["S14: Scientific Evaluation & MLOps"]
        S15["S15: Governed Data Products"]
    end

    %% Dependencies between layers
    M00 --> M02
    M01 --> M02
    S16 --> M03
    M02 --> M03
    M02 --> M04
    M03 --> S1
    M04 --> S1
    S0 --> M04

    M04 --> S2
    M04 --> S3
    M04 --> S4
    M04 --> S5
    M04 --> S6
    M04 --> S7

    S2 --> S8
    S3 --> S8
    S4 --> S8
    S7 --> S8

    S3 --> S10
    S4 --> S10
    S5 --> S10
    S6 --> S10

    S8 --> CB
    S10 --> CB
    S5 --> CB
    S2 --> CB
    S3 --> CB
    S4 --> CB

    CB --> S12
    S9 --> S12
    S11 --> S12

    CB --> CP
    S7 --> CP
    CB --> RM
    M04 --> SYNC
    S10 --> NOTIF
    S8 --> NOTIF

    S8 --> S14
    S10 --> S14
    M03 --> S15
```

---

## 2. Ingestion & Deterministic Execution Pipeline

A critical architectural mandate is that **deterministic physical calculations occur before AI invocation**. Conversational AI never estimates physical variables.

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Farmer (Mobile App)
    participant Receptor as Chat Receptor API (/chat/receptor)
    participant Speech as Speech Service (STT)
    participant Vision as Leaf Vision Service (IPM)
    participant Builder as Agricultural Context Builder
    participant Weather as Weather Service (IMD/OWM)
    participant Hydro as FAO-56 Hydrology Engine
    participant Hazard as Hazard State Machine
    participant AI as Grounded Gemini Gateway
    participant TTS as Indic-TTS Synthesizer

    Farmer->>Receptor: POST (device_id, query_text / audio_file / image_file)
    
    alt Audio file provided
        Receptor->>Speech: Transcribe audio to text (IndicWhisper/Bhashini)
        Speech-->>Receptor: Transcribed vernacular query
    end

    alt Image file provided
        Receptor->>Vision: Diagnose leaf symptoms (CIB&RC IPM Rules)
        Vision-->>Receptor: LeafDiagnosisResult (Condition, IPM, Dosage)
    end

    Receptor->>Builder: Build live context (db, profile, plot)
    Builder->>Weather: Fetch live weather / agro-climatic normal
    Weather-->>Builder: WeatherSnapshot (Tmax, Tmin, Rain24h)
    
    Builder->>Hydro: Calculate Penman-Monteith ET0, TAW, RAW, Depletion
    Hydro-->>Builder: WaterBalanceOutput (Trigger: IRRIGATE/HOLD/DRAIN, mm)
    
    Builder->>Hazard: Evaluate FSM (Rain forecast, Groundwater, Slope)
    Hazard-->>Builder: HazardEvaluationResult (State, Restrictions, Directives)

    Builder-->>Receptor: Consolidated AgriculturalContextPacket

    Receptor->>AI: Generate grounded response (Context + ICAR Prompt + Query)
    Note over AI: Enforces Hazard Directives<br/>(e.g., HALT_ALL_CHEMICALS)
    AI-->>Receptor: Text advisory in vernacular language

    Receptor->>TTS: Synthesize reply text to audio
    TTS-->>Receptor: Base64 WAV audio Data URL

    Receptor->>Farmer: JSON Response (session_id, reply_text, audio_url, hazard_state)
```

---

## 3. Comprehensive Module Dependency Matrix

| Module ID | Module Name | Upstream Dependencies | Downstream Consumers | Primary Data Contract |
|---|---|---|---|---|
| **M00** | Core Foundation | Python 3.12, FastAPI, Pydantic | All modules | App lifecycle, settings, DB session |
| **M01** | Shared Contracts | Pydantic v2 | API Routers, Services | Pydantic Request/Response models |
| **M02** | Database Engine | SQLAlchemy 2.0, GeoAlchemy2, PostGIS | Repositories, Services | ORM Models, Session generator |
| **M03** | Identity & Consent | `M00`, `M02`, `S16` | `M04`, `S1`, `S12`, `S15` | `DeviceProfileResponse`, `UserToken` |
| **M04** | Plot Registry | `M02`, `M03`, Shapely | `S1`, `S2`, `S4`, `S6`, Context Builder | `PlotResponse`, `CropCycleResponse` |
| **S0** | Reference Geography | Python stdlib | `M04`, `S3`, `S4` | District medians, Admin codes |
| **S1** | Onboarding Orchestration | `M03`, `M04`, Context Builder | Mobile Client bootstrap | `BootstrapResponse` |
| **S2** | Soil Intelligence | `M02`, `M04` | `S8`, Context Builder, Crop Planner | `SoilHealthResponse`, Benchmarks |
| **S3** | Weather & Climate | `httpx`, OpenWeatherMap, IMD | `S8`, `S10`, Context Builder | `WeatherSnapshot` |
| **S4** | Water Resources | `M02`, `M04` | `S8`, `S10`, Context Builder | `GroundwaterResponse`, CGWB median |
| **S5** | Satellite STAC | `httpx`, Element84 STAC | `S10`, Context Builder | `VegetationIndices` (NDVI, NDWI) |
| **S6** | Terrain & DEM | `M04`, GeoTIFF / DEM | `S10` | Elevation (m), Slope (%) |
| **S7** | Crop Knowledge Base | Python stdlib / DB | `S5`, `S8`, Crop Planner | `FAO56_CROP_PARAMETERS` ($K_c, Z_r, p$) |
| **S8** | FAO-56 Hydrology Engine | `S2`, `S3`, `S4`, `S7` | Context Builder, Notifications | `WaterBalanceOutput` (IRRIGATE/HOLD/DRAIN) |
| **S9** | Leaf Vision & Yield | `httpx`, Gemini Vision, CIB Rules | `S12` | `LeafDiagnosisResult` |
| **S10** | Hazard State Machine | `S3`, `S4`, `S5`, `S6` | Context Builder, Notifications | `HazardEvaluationResult` (Restrictions) |
| **S11** | Knowledge Retrieval (RAG) | PostgreSQL tsvector / pgvector | `S12` | Verified ICAR document citations |
| **S12** | Gemini Chat Gateway | `S8`, `S9`, `S10`, `S11`, Speech | Mobile Client | `ChatReceptorResponse` |
| **S13** | Farmer Workflows | `M04`, `S7`, `S8`, `S10` | Mobile Client | Suitability scores, Milestones, Sync |
| **S14** | Scientific Evaluation | Pytest, Benchmarks | CI/CD | Benchmark validation reports |
| **S15** | Governed Data Products | `M02`, `M03` | External analytics | Anonymized k-anonymous aggregations |
| **S16** | Privacy and Security | Python `hashlib`, PyJWT | All API Routers | JWT tokens, Auth dependencies |

---

## 4. Circular Dependency Audit

An analysis of import paths across `backend/app/` reveals:
- `core/` has **zero** dependencies on `models/`, `api/`, `services/`, or `engines/`.
- `models/` depends only on `core/database.py`.
- `schemas/` depends only on Pydantic and standard library.
- `engines/` depend only on standard library, mathematical formulas, and `services/fallback_data.py`. They have **zero** dependencies on database models, ORM sessions, or external APIs.
- `services/` depend on `models/`, `engines/`, and `core/config.py`.
- `api/` depends on `services/`, `models/`, `schemas/`, and `core/`.

**Verdict**: The dependency structure is strictly acyclic and respects clean layering boundaries.

