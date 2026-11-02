# 📡 Krishi Mitra / AgriNova — Backend API Inventory

**Author**: Senior Backend Architect  
**Audit Date**: October 30, 2026  
**Base URL**: `http://localhost:8000/api/v1`  
**OpenAPI Docs**: `http://localhost:8000/docs`  

---

## 1. Existing Endpoints Inventory

Below is the exhaustive catalog of every active route currently implemented in the FastAPI application.

### Category: Health & Diagnostics
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/health` | `liveness_check` | [`app/main.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/main.py#L225) | None | 200 OK |
| `GET` | `/ready` | `readiness_check` | [`app/main.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/main.py#L240) | None | 200 OK / 503 Service Unavailable |
| `GET` | `/` | `root_status` | [`app/main.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/main.py#L295) | None | 200 OK |
| `GET` | `/healthz` | `healthz` | [`app/main.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/main.py#L305) | None | 200 OK |

- **`GET /health`** (Liveness Probe):
  - Request: None.
  - Response: `{"status": "pass", "service": "Krishi Mitra Agricultural Backend", "version": "1.0.0", "timestamp": "..."}`
  - Guarantees: Confirms process is running; zero dependency on database or storage.
- **`GET /ready`** (Readiness Probe):
  - Request: None.
  - Response (Healthy): `{"status": "pass", "service": "...", "version": "1.0.0", "timestamp": "...", "checks": {"database": "pass", "storage": "pass"}}` (200 OK)
  - Response (Degraded): `{"status": "fail", "service": "...", "version": "1.0.0", "timestamp": "...", "checks": {"database": "fail", "storage": "pass"}, "detail": "One or more required subsystem readiness checks failed."}` (503 Service Unavailable)
  - Guarantees: Real `SELECT 1` ping and storage write canary; never exposes credentials or internal paths.
- **`GET /`**:
  - Request: None.
  - Response: `{"status": "healthy", "service": "Krishi Mitra Agricultural Backend", "version": "1.0.0", "environment": "development"}`
- **`GET /healthz`**:
  - Request: None.
  - Response: `{"status": "ok"}` (Preserved for backward compatibility)

---

### Category: App Startup Bootstrap & Onboarding
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/bootstrap` | `bootstrap_app` | [`app/api/v1/bootstrap.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/bootstrap.py#L14) | None (Query `device_id`) | 200 OK |
| `POST` | `/api/v1/bootstrap/onboard` | `onboard_device` | [`app/api/v1/bootstrap.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/bootstrap.py#L55) | None | 201 Created |

---

### Category: Farmer Identity & Authentication
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | `register_farmer` | [`app/api/v1/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/auth.py#L38) | None | 201 Created |
| `POST` | `/api/v1/auth/login-pin` | `login_with_pin` | [`app/api/v1/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/auth.py#L112) | None | 200 OK / 401 Unauthorized |
| `POST` | `/api/v1/auth/device-session` | `establish_device_session` | [`app/api/v1/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/auth.py#L160) | None | 200 OK |
| `GET` | `/api/v1/auth/me` | `get_current_profile` | [`app/api/v1/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/auth.py#L205) | Bearer JWT or `X-Device-ID` | 200 OK / 401 Unauthorized |

---

### Category: Consent & DPDP Compliance
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/consent/grant` | `grant_consent` | [`app/api/v1/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/consent.py#L28) | Bearer JWT or `X-Device-ID` | 200 OK |
| `POST` | `/api/v1/consent/revoke` | `revoke_consent` | [`app/api/v1/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/consent.py#L75) | Bearer JWT or `X-Device-ID` | 200 OK |
| `GET` | `/api/v1/consent/status` | `get_consent_status` | [`app/api/v1/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/consent.py#L122) | Bearer JWT or `X-Device-ID` | 200 OK |
| `GET` | `/api/v1/consent/audit-logs` | `get_audit_trail` | [`app/api/v1/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/consent.py#L145) | Bearer JWT or `X-Device-ID` | 200 OK |

---

### Category: Farm Holdings & Multi-Plot Management
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/farms` | `create_farm` | [`app/api/v1/farms.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/farms.py#L38) | Bearer JWT or `X-Device-ID` | 201 Created |
| `GET` | `/api/v1/farms` | `list_farms` | [`app/api/v1/farms.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/farms.py#L70) | Bearer JWT or `X-Device-ID` | 200 OK |
| `GET` | `/api/v1/farms/{farm_id}` | `get_farm` | [`app/api/v1/farms.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/farms.py#L96) | Bearer JWT or `X-Device-ID` | 200 OK / 403 Forbidden / 404 Not Found |
| `GET` | `/api/v1/farms/{farm_id}/plots` | `get_farm_multi_plots` | [`app/api/v1/farms.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/farms.py#L112) | Bearer JWT or `X-Device-ID` | 200 OK / 403 Forbidden / 404 Not Found |
| `DELETE` | `/api/v1/farms/{farm_id}` | `delete_farm` | [`app/api/v1/farms.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/farms.py#L137) | Bearer JWT or `X-Device-ID` | 200 OK / 403 Forbidden / 404 Not Found |

---

### Category: Environmental Observations & Spatial Ingestion (Milestone C)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/plots/{plot_id}/weather/history` | `get_plot_weather_history` | [`app/api/v1/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/observations.py#L42) | None / Dual-Mode | 200 OK / 404 Not Found |
| `GET` | `/api/v1/plots/{plot_id}/satellite/timeseries` | `get_plot_satellite_timeseries` | [`app/api/v1/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/observations.py#L94) | None / Dual-Mode | 200 OK / 404 Not Found |
| `GET` | `/api/v1/plots/{plot_id}/terrain` | `get_plot_terrain` | [`app/api/v1/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/observations.py#L152) | None / Dual-Mode | 200 OK / 404 Not Found |
| `POST` | `/api/v1/plots/{plot_id}/sync-environmental` | `sync_plot_environmental_data` | [`app/api/v1/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/observations.py#L173) | None / Dual-Mode | 200 OK / 404 Not Found |

---

#### Detailed Route Specifications:

#### `GET /api/v1/bootstrap`
- **Purpose**: App launch synchronization. Checks onboarding, resolves active plot, queries live environmental layers, and runs FAO-56 and Hazard engines in a single round-trip.
- **Query Parameters**: `device_id: str` (required)
- **Request Body**: None.
- **Response Schema**: `BootstrapResponse`
  - `device_id: str`
  - `is_onboarded: bool`
  - `message: str`
  - `profile: Optional[DeviceProfileResponse]`
  - `active_plot_id: Optional[int]`
  - `context: Optional[dict]` (contains `weather`, `groundwater`, `soil_nutrients`, `satellite`, `hydrology`, `hazard`)
  - `hazard_state: Optional[str]` (`NORMAL_MODE`, `STORM_FLOOD_MODE`, `EL_NINO_DROUGHT_MODE`)
  - `enforced_restrictions: list[str]`
- **Database Tables Touched**: `device_profiles` (read), `farm_plots` (read), `crop_cycles` (read), `groundwater_observations` (read), `soil_health_records` (read).
- **Engines Invoked**: `fao56_hydrology.py`, `hazard_state.py`, `satellite_stac.py`, `weather_service.py`.
- **Existing Test**: `test_bootstrap_endpoint` in `backend/tests/test_chat_receptor.py`.
- **Test Result**: **PASS**.
- **Limitations**: If `device_id` does not exist, returns `is_onboarded=False` with empty context.

#### `POST /api/v1/bootstrap/onboard`
- **Purpose**: Create or update farmer profile associated with the hardware device UUID.
- **Request Body**: `DeviceProfileCreate`
  ```json
  {
    "device_id": "DEV-12345",
    "farmer_name": "Rameshwar Patil",
    "preferred_language": "hi",
    "phone_number": "+919876543210",
    "kisan_id": "PMK-123456"
  }
  ```
- **Response Schema**: `DeviceProfileResponse` (Status: `201 Created`)
- **Database Tables Touched**: `device_profiles` (upsert).
- **Existing Test**: Tested via conftest seed fixture.
- **Test Result**: **PASS**.
- **Limitations**: No phone number OTP verification or authentication credentials issued.

---

### Category: Farm Plots & Field Boundaries
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/plots` | `create_farm_plot` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L37) | None | 201 Created |
| `GET` | `/api/v1/plots` | `list_farm_plots` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L86) | None (Query `device_id`) | 200 OK |
| `GET` | `/api/v1/plots/{plot_id}` | `get_plot_details` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L96) | None | 200 OK |
| `POST` | `/api/v1/plots/{plot_id}/crop-cycle` | `register_crop_cycle` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L107) | None | 201 Created |
| `POST` | `/api/v1/plots/{plot_id}/groundwater` | `add_groundwater_observation` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L136) | None | 201 Created |
| `POST` | `/api/v1/plots/{plot_id}/soil-health` | `add_soil_health_record` | [`app/api/v1/plots.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/plots.py#L156) | None | 201 Created |

#### Detailed Route Specifications:

#### `POST /api/v1/plots`
- **Purpose**: Register field boundary polygon, auto-calculate centroid coordinates and geodesic area in hectares.
- **Request Body**: `PlotCreateRequest`
  ```json
  {
    "device_id": "DEV-12345",
    "name": "East Field",
    "survey_number": "142/A",
    "khasra_number": "K-88",
    "boundary": {
      "type": "Polygon",
      "coordinates": [[[78.5000, 17.5000], [78.50094, 17.5000], [78.50094, 17.5009], [78.5000, 17.5009], [78.5000, 17.5000]]]
    },
    "soil_texture": "Vertisol",
    "elevation_m": 250.0,
    "slope_percent": 1.5
  }
  ```
- **Response Schema**: `PlotResponse`
- **Database Tables Touched**: `farm_plots` (insert).
- **Existing Test**: `test_create_and_list_plots` in `backend/tests/test_plots_api.py`.
- **Test Result**: **PASS**.
- **Limitations**: Deactivates prior plots on the device (`is_active = False`).

#### `POST /api/v1/plots/{plot_id}/crop-cycle`
- **Purpose**: Register active crop cycle, growth stage, variety, and irrigation method.
- **Request Body**: `CropCycleCreateRequest`
  ```json
  {
    "crop_name": "Cotton",
    "variety": "Bt-Cotton",
    "sowing_date": "2026-06-15",
    "growth_stage": "FLOWERING",
    "irrigation_method": "DRIP"
  }
  ```
- **Response Schema**: `CropCycleResponse`
- **Database Tables Touched**: `crop_cycles` (insert).
- **Existing Test**: `test_register_crop_cycle_and_telemetry` in `backend/tests/test_plots_api.py`.
- **Test Result**: **PASS**.

#### `POST /api/v1/plots/{plot_id}/groundwater`
- **Purpose**: Log groundwater level observation in mbgl.
- **Request Body**: `GroundwaterCreateRequest` (`depth_mbgl: float`, `source_type: str`).
- **Response Schema**: `GroundwaterResponse`
- **Database Tables Touched**: `groundwater_observations` (insert).
- **Existing Test**: `test_register_crop_cycle_and_telemetry` in `backend/tests/test_plots_api.py`.
- **Test Result**: **PASS**.

#### `POST /api/v1/plots/{plot_id}/soil-health`
- **Purpose**: Record Soil Health Card physicochemical parameters.
- **Request Body**: `SoilHealthCreateRequest` (`nitrogen_kg_ha`, `phosphorus_kg_ha`, `potassium_kg_ha`, `ph`, `organic_carbon_percent`, `source_type`).
- **Response Schema**: `SoilHealthResponse`
- **Database Tables Touched**: `soil_health_records` (insert).
- **Existing Test**: `test_register_crop_cycle_and_telemetry` in `backend/tests/test_plots_api.py`.
- **Test Result**: **PASS**.

---

### Category: Conversational Chat Receptor
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/chat/receptor` | `chat_receptor_endpoint` | [`app/api/v1/chat_receptor.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/chat_receptor.py#L225) | None | 200 OK |

- **Purpose**: Unified Voice / Vision / Text conversational receptor. Transcribes audio, analyzes leaf images, retrieves prior 5 turns of conversation, computes live agricultural context, enforces hazard overrides, and returns synthesized audio + text grounded in ICAR system instructions.
- **Request Content Types**: Supports both `application/json` and `multipart/form-data`.
- **Form / Body Fields**:
  - `device_id: str` (required)
  - `session_id: Optional[str]` (if empty or `"new"`, a new UUID session is generated)
  - `query_text: Optional[str]`
  - `language: Optional[str]` (`hi`, `te`, `mr`, `en`)
  - `audio_file: Optional[UploadFile]` (WAV / MP3 audio stream)
  - `image_file: Optional[UploadFile]` (JPEG / PNG leaf photo)
- **Response Schema**: `ChatReceptorResponse`
  - `session_id: str`
  - `reply_text: str`
  - `audio_base64_url: str` (`data:audio/wav;base64,...`)
  - `hazard_state: str`
  - `injected_context: dict`
- **Database Tables Touched**: `chat_sessions` (read/insert), `chat_messages` (read/insert), all context tables.
- **Engines & Services Invoked**: `SpeechService`, `LeafVisionService`, `ContextBuilder`, `FAO56Hydrology`, `HazardStateMachine`, Gemini 2.5 Flash.
- **Existing Tests**: 3 integration tests in `backend/tests/test_chat_receptor.py`.
- **Test Result**: **PASS**.
- **Limitations**: No token authentication on chat session resumption.

---

## 2. Target Missing Endpoints (Roadmap Inventory)

The following endpoints are required by the Target Architecture milestones:

### Milestone A: Observability Probes [COMPLETED]
- `GET /health`: Liveness probe verifying process health. (Implemented & Tested)
- `GET /ready`: Readiness probe verifying active database connection (`SELECT 1`) and storage read/write. (Implemented & Tested)

### Milestone B: Identity, Auth & Consent (M03)
- `POST /api/v1/auth/register`: Create user account with phone and credentials.
- `POST /api/v1/auth/token`: Authenticate user and issue JWT access token.
- `POST /api/v1/auth/refresh`: Refresh expired JWT access token.
- `GET /api/v1/consent`: List active consents for authenticated farmer.
- `POST /api/v1/consent`: Record specific agricultural data processing consent.
- `POST /api/v1/consent/{consent_id}/withdraw`: Withdraw consent and log audit trail.

### Milestone C: Farms & Multi-Plot Aggregation (M04)
- `POST /api/v1/farms`: Create a Farm holding multiple plots.
- `GET /api/v1/farms`: List all farms and their member plots.

### Milestone D: Knowledge Retrieval (S11)
- `GET /api/v1/knowledge/search`: Full-text search of approved ICAR packages of practices.

### Milestone E: Farmer Workflows (S13)
- `POST /api/v1/planner/suitability`: Rank crops by soil, climate, water, and market feasibility.
- `GET /api/v1/roadmap/{crop_cycle_id}`: Retrieve milestone checkpoints and agronomic schedule.
- `POST /api/v1/roadmap/{checkpoint_id}/complete`: Mark crop cycle checkpoint complete.
- `POST /api/v1/sync/push`: Push offline client mutations with idempotency key.
- `GET /api/v1/sync/pull`: Pull server-side state delta since timestamp.
- `GET /api/v1/notifications`: List active hazard and irrigation notifications.
- `POST /api/v1/notifications/{id}/read`: Mark notification as read.

