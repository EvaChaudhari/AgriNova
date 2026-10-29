# 🌾 Krishi Mitra — Production Backend Engine

Krishi Mitra is an open-source, voice-first digital agriculture platform tailored for smallholder farmers in India.
It enforces a **strict separation of concerns**: pure deterministic hydrological and meteorological hazard engines execute first; multimodal conversational AI (Gemini / Agri-SLM) serves strictly as an empathetic vernacular translation and conversational grounding layer.

---

## 🏛️ Architectural Blueprint & Principles

1. **Separation of Physics and Conversation**: Deterministic agronomic engines (FAO-56 Penman-Monteith, Hazard State Machine, STAC/Phenological models) evaluate all physical variables and hard constraints prior to any conversational AI invocation. The AI translation layer cannot override physical or safety constraints.
2. **Single-Tenant per Hardware Device**: Strictly one profile per physical device bound to `device_id` / hardware UUID. No multi-tenant SSO overhead.
3. **Deterministic Regional Fallback Ingestion**: Ingests data through a 3-tier hierarchy (`Hardware Sensor` -> `Public Government API` -> `Regionally Calibrated Baselines`), ensuring zero operational downtime even when government portals or IoT sensors are offline.

```
┌────────────────────────────────────────────────────────┐
│                   Unified Client                        │
│       (Voice Audio, Leaf Photo, or Text Query)         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI App (/api/v1/chat/receptor)         │
├───────────────────────────┬────────────────────────────┤
│ 1. Multimodal Translation │ STT (Bhashini/IndicWhisper)│
│                           │ Vision (CIB Leaf Pathology)│
├───────────────────────────┼────────────────────────────┤
│ 2. Ingestion Hierarchy    │ Telemetry -> API -> Baseline│
│    (Context Resolution)   │ Groundwater: CGWB Median   │
│                           │ Weather: IMD Climatology   │
│                           │ Soil: SHC Benchmark        │
│                           │ Satellite: STAC / Phenology│
├───────────────────────────┼────────────────────────────┤
│ 3. Pure Deterministic     │ FAO-56 Penman-Monteith     │
│    Scientific Engines     │ Hazard State Machine (FSM) │
├───────────────────────────┼────────────────────────────┤
│ 4. Grounded AI Layer      │ ICAR Principal Scientist   │
│                           │ Prompt with Enforced Hazard│
├───────────────────────────┼────────────────────────────┤
│ 5. Vernacular Output      │ Text + TTS Base64 Audio    │
└────────────────────────────────────────────────────────┘
```

---

## 📂 Directory Layout

```text
backend/
├── alembic/                     # Database migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                  # FastAPI application entry point & CORS
│   ├── core/
│   │   ├── config.py            # Pydantic v2 application settings
│   │   └── database.py          # PostGIS Geometry & SQLAlchemy session
│   ├── models/                  # SQLAlchemy + GeoAlchemy2 PostGIS models
│   │   ├── profile.py           # DeviceProfile (device_id hardware UUID)
│   │   ├── plot.py              # FarmPlot (Polygon, centroid, area) & CropCycle
│   │   ├── telemetry.py         # GroundwaterObservation & SoilHealthRecord
│   │   └── chat.py              # ChatSession & ChatMessage
│   ├── schemas/                 # Pydantic v2 schemas
│   │   ├── bootstrap.py         # DeviceProfile & Bootstrap response schemas
│   │   ├── geospatial.py        # GeoJSON Polygon, Plot & Telemetry schemas
│   │   └── chat.py              # Chat receptor request & response schemas
│   ├── engines/                 # Pure deterministic scientific engines
│   │   ├── fao56_hydrology.py   # FAO-56 Penman-Monteith ET0, TAW, RAW, depletion
│   │   ├── hazard_state.py      # Normal vs El Niño vs Storm/Flood state machine
│   │   └── satellite_stac.py    # Sentinel-2 STAC NDVI/NDWI + synthetic fallback
│   ├── services/
│   │   ├── fallback_data.py     # CGWB groundwater, IMD normals, FAO-56 coefficients
│   │   ├── weather_service.py   # IMD / OpenWeatherMap adapter + fallback
│   │   ├── speech_service.py    # Bhashini ULCA / IndicWhisper STT & Indic-TTS
│   │   ├── vision_service.py    # Leaf pathology validator (CIB IPM guidelines)
│   │   └── context_builder.py   # Assembles live agricultural context packet
│   └── api/v1/
│       ├── bootstrap.py         # GET /api/v1/bootstrap & farmer onboarding
│       ├── plots.py             # Field polygon registration & PostGIS CRUD
│       └── chat_receptor.py     # Unified Voice / Vision / Text chat receptor
├── tests/
│   ├── conftest.py              # Pytest fixtures and test database setup
│   ├── test_fao56.py            # FAO-56 Penman-Monteith & water balance tests
│   ├── test_hazard_state.py     # Hazard state machine & directive tests
│   ├── test_chat_receptor.py    # Conversational memory & override tests
│   ├── test_plots_api.py        # Field polygon & PostGIS CRUD tests
│   └── test_services.py         # Vision, weather, speech, and satellite tests
└── requirements.txt
```

---

## ⚡ Quickstart

### 1. Environment Setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Run Database Migrations
```bash
cd backend
alembic upgrade head
```

### 3. Run the Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be accessible at: `http://localhost:8000/docs`.

### 4. Execute the Test Suite
```bash
PYTHONPATH=backend pytest -v
```

---

## 🔬 Core Scientific Engines

### 1. FAO-56 Hydrological Engine (`fao56_hydrology.py`)
Computes reference evapotranspiration ($ET_0$) using the FAO-56 Penman-Monteith equation:
$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T_{\text{mean}} + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$
Tracks daily root zone depletion:
$$D_t = D_{t-1} + ET_c - P_{\text{eff}} - GW_{\text{capillary}}$$
Triggers:
- `IRRIGATE`: when $D_t \ge RAW$ ($RAW = p \times TAW$).
- `DRAIN`: when soil is oversaturated from storm rainfall.
- `HOLD`: when root depletion is within safe buffering capacity.

### 2. Extreme Weather Hazard Engine (`hazard_state.py`)
Deterministic finite state machine with strict priority rules:
- **`STORM_FLOOD_MODE`** (24h rain $\ge 50\text{ mm}$ or waterlogged):
  - Enforces `HALT_ALL_CHEMICAL_SPRAYING`, `HALT_FERTILIZERS`, `CLEAR_DRAINAGE_FURROWS`.
  - DEM slope $> 3\% \implies$ `HIGH_TOPSOIL_EROSION_RISK` alert.
  - DEM slope $\le 3\% \implies$ `ROOT_ASPHYXIATION_RISK` alert.
- **`EL_NINO_DROUGHT_MODE`** (Groundwater $> 18\text{ mbgl}$ & seasonal deficit $> 35\%$):
  - Enforces `FORBID_SURFACE_FLOOD_IRRIGATION`. Recommends night-time drip and straw mulching.
  - Sub-mode `CRITICAL_WATER_STRESS`: Triggered when NDWI $< -0.20$.
- **`NORMAL_MODE`**: Default operating envelope.

### 3. Pest Leaf Vision Validator (`vision_service.py`)
- Zero-hallucination policy adhering to Central Insecticides Board (CIB&RC) registrations.
- Recommends non-chemical Integrated Pest Management (IPM) first: NSKE 5%, pheromone traps, trichoderma, bio-control.
- Prescribes exact dilution rates (e.g. per 15L sprayer tank) and mandatory pre-harvest intervals (PHI).

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/bootstrap?device_id=...` | Launch state sync, environmental layers & engine evaluation |
| `POST` | `/api/v1/bootstrap/onboard` | Register/update farmer profile (one per device) |
| `POST` | `/api/v1/plots` | Register polygon boundary with auto-centroid & area |
| `GET` | `/api/v1/plots?device_id=...` | List farm plots for device |
| `POST` | `/api/v1/plots/{id}/crop-cycle` | Register active crop cycle & growth stage |
| `POST` | `/api/v1/plots/{id}/groundwater` | Log groundwater sensor / WRIS depth |
| `POST` | `/api/v1/plots/{id}/soil-health` | Log Soil Health Card NPK, pH & OC |
| `POST` | `/api/v1/chat/receptor` | Unified Voice/Vision/Text receptor with grounded advisory |

