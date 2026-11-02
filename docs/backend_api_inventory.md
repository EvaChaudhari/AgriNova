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
| `POST` | `/api/v1/auth/logout` | `logout_user` | [`app/api/v1/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/auth.py#L235) | Bearer JWT | 200 OK / 401 Unauthorized |
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

### Category: Crop Knowledge Base (Milestone D)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/crops` | `list_crops` | [`app/api/v1/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/crop_knowledge.py#L22) | Optional | 200 OK |
| `GET` | `/api/v1/crops/{crop_id}` | `get_crop_detail` | [`app/api/v1/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/crop_knowledge.py#L36) | Optional | 200 OK / 404 |
| `GET` | `/api/v1/crops/{crop_id}/stage-at-das` | `get_stage_at_das` | [`app/api/v1/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/crop_knowledge.py#L48) | Optional | 200 OK / 404 |

- **Purpose**: Query versioned agronomic taxonomy, cultivar varieties, FAO-56 growth stages ($K_c$, $Z_r$, $p$), ICAR STCR fertilizer coefficients, and stage-specific IPM pest vulnerabilities.
- **Query Parameters**:
  - `GET /crops`: `season` (`KHARIF`, `RABI`, `ZAID`), `category` (`CEREAL`, `PULSE`, `OILSEED`, `FIBRE`, `CASH`).
  - `GET /crops/{crop_id}/stage-at-das`: `das` (Day After Sowing, integer >= 0).
- **Response Schemas**: `list[CropSummaryResponse]`, `CropDetailResponse`, `StageAtDASResponse`.
- **Database Tables Touched**: `crops`, `crop_varieties`, `crop_growth_stages`, `crop_nutrient_benchmarks`, `crop_pest_profiles`.
- **Existing Tests**: 8 tests in `backend/tests/test_crop_knowledge.py`.
- **Test Result**: **PASS**.

---

### Category: Soil Intelligence & Fertilizer Recommendations (Milestone D)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/plots/{plot_id}/soil` | `ingest_plot_soil_health` | [`app/api/v1/soil.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/soil.py#L26) | Optional | 201 Created |
| `GET` | `/api/v1/plots/{plot_id}/soil/rating` | `get_plot_soil_rating` | [`app/api/v1/soil.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/soil.py#L65) | Optional | 200 OK |
| `POST` | `/api/v1/plots/{plot_id}/fertilizer-recommendation` | `compute_fertilizer_recommendation` | [`app/api/v1/soil.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/soil.py#L97) | Optional | 200 OK |

- **Purpose**: Ingest Soil Health Card lab results, evaluate qualitative fertility tiers (Low/Medium/High) and composite Soil Health Index (0-100), and compute targeted-yield STCR fertilizer requirements converted to commercial 50kg bags (DAP, Urea, MOP) with stage-wise split schedules and ICAR safe upper bound clamping.
- **Request Schemas**: `SoilHealthCardCreate`, `FertilizerRecommendationRequest`.
- **Response Schemas**: `PlotSoilRatingResponse`, `FertilizerRecommendationResponse`.
- **Database Tables Touched**: `soil_health_records`, `farm_plots`, `crop_cycles`, `crops`, `crop_nutrient_benchmarks`.
- **Engines & Services Invoked**: `FertilizerEngine`, `SoilIngestionService`.
- **Existing Tests**: 6 tests in `backend/tests/test_soil_api.py`, 6 tests in `backend/tests/test_fertilizer_engine.py`.
- **Test Result**: **PASS**.

---

### Category: Crop Suitability Planner (Milestone E)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/planner/recommend-crops` | `recommend_crops_for_plot` | [`app/api/v1/planner.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/planner.py#L38) | Optional | 200 OK |

- **Purpose**: Multi-criteria crop suitability evaluation assessing soil texture, pH, regional groundwater table, and irrigation infrastructure. Categorizes risk into `OPTIMAL`, `SUITABLE_WITH_IRRIGATION`, and `HIGH_RISK_DROUGHT`.
- **Request Schema**: `CropRecommendationRequest` (`plot_id`, `season`, `preferred_category`).
- **Response Schema**: `CropRecommendationResponse`.
- **Database Tables Touched**: `crop_plans` (insert), `farm_plots` (read), `crops` (read), `crop_varieties` (read), `soil_health_records` (read), `groundwater_observations` (read).
- **Engines Invoked**: `CropPlannerEngine`.
- **Existing Tests**: 6 tests in `backend/tests/test_crop_planner.py`.
- **Test Result**: **PASS**.

---

### Category: Crop Roadmaps & Checkpoints (Milestone E)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/plots/{plot_id}/roadmap` | `get_plot_roadmap` | [`app/api/v1/roadmap.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/roadmap.py#L25) | Optional | 200 OK |
| `POST` | `/api/v1/plots/{plot_id}/checkpoints/{checkpoint_id}/complete` | `complete_roadmap_checkpoint` | [`app/api/v1/roadmap.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/roadmap.py#L44) | Optional | 200 OK |

- **Purpose**: Generates and retrieves the 6-milestone agronomic calendar for an active crop cycle, tracking days after sowing (DAS), active phenological stage, progress percentage, and field notes.
- **Request Schema**: `CheckpointCompleteRequest` (`notes`, `status`).
- **Response Schemas**: `CropRoadmapResponse`, `RoadmapCheckpointResponse`.
- **Database Tables Touched**: `crop_roadmaps`, `roadmap_checkpoints`, `farm_plots`, `crop_cycles`.
- **Engines Invoked**: `RoadmapEngine`.
- **Existing Tests**: 5 tests in `backend/tests/test_roadmap_engine.py`.
- **Test Result**: **PASS**.

---

### Category: Offline Synchronization (Milestone E)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `POST` | `/api/v1/sync/batch` | `synchronize_offline_batch` | [`app/api/v1/sync.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/sync.py#L18) | Optional | 200 OK |

- **Purpose**: Idempotent batch reconciliation of offline actions (checkpoint completion, irrigation events, field notes) queued on rural 2G/3G mobile devices.
- **Request Schema**: `SyncBatchRequest` (`device_id`, list of `SyncActionItem` each with client `idempotency_key`).
- **Response Schema**: `SyncBatchResponse` (`applied`, `skipped`, list of `SyncActionResult`).
- **Database Tables Touched**: `offline_sync_events` (read/insert), `roadmap_checkpoints` (update).
- **Services Invoked**: `OfflineSyncService`.
- **Existing Tests**: 2 integration tests in `backend/tests/test_offline_sync.py`.
- **Test Result**: **PASS**.

---

### Category: Farmer Notifications (Milestone E)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/notifications` | `get_farmer_notifications` | [`app/api/v1/notifications.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/notifications.py#L22) | Optional | 200 OK |
| `POST` | `/api/v1/notifications/{notification_id}/read` | `acknowledge_notification` | [`app/api/v1/notifications.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/notifications.py#L36) | Optional | 200 OK |

- **Purpose**: Retrieve and acknowledge actionable farmer alerts (weather hazards, irrigation deficits, roadmap milestone reminders) localized in Hindi, Marathi, Telugu, or English.
- **Query Parameters**: `device_id` (required), `unread_only` (optional boolean).
- **Response Schemas**: `list[NotificationResponse]`, `NotificationReadResponse`.
- **Database Tables Touched**: `farmer_notifications` (read/update).
- **Services Invoked**: `NotificationService`.
- **Existing Tests**: 4 tests in `backend/tests/test_notifications_api.py`.
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

### Category: Scientific Evaluation & Quality Assurance (Milestone F)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/evaluation/scientific-benchmarks` | `get_scientific_benchmarks` | [`app/api/v1/evaluation.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/evaluation.py#L22) | None / Dual-Mode | 200 OK |
| `GET` | `/api/v1/evaluation/plot/{plot_id}/quality-report` | `get_plot_quality_report` | [`app/api/v1/evaluation.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/evaluation.py#L38) | None / Dual-Mode | 200 OK / 404 Not Found |

- **`GET /api/v1/evaluation/scientific-benchmarks`**:
  - Purpose: Validates FAO-56 Penman-Monteith ET0 calculations against ICAR lysimeter benchmark datasets across Indian agro-climatic zones (tolerances <= 5.0%).
  - Response Schema: `ScientificBenchmarkReport` (contains per-benchmark items, relative error %, and overall suite status).
- **`GET /api/v1/evaluation/plot/{plot_id}/quality-report`**:
  - Purpose: Computes plot telemetry data completeness %, sensor freshness in hours, sensor anomalies, and agronomic uncertainty score (0.05–0.95) with quality grade (`EXCELLENT`, `GOOD`, `ADEQUATE`, `DEGRADED`).
  - Response Schema: `PlotQualityReport`.

---

### Category: Governed Data Products & Parametric Insurance (Milestone F)
| Method | Path | Handler | File Location | Auth | Status |
|---|---|---|---|---|---|
| `GET` | `/api/v1/governed/fpo/crop-summary` | `get_fpo_crop_summary` | [`app/api/v1/governed_data.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/governed_data.py#L22) | None / Dual-Mode | 200 OK |
| `GET` | `/api/v1/governed/insurance/drought-index` | `get_insurance_drought_index` | [`app/api/v1/governed_data.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/api/v1/governed_data.py#L39) | None / Dual-Mode | 200 OK |

- **`GET /api/v1/governed/fpo/crop-summary`**:
  - Purpose: Produces DPDP Act-compliant, de-identified collective crop acreage and active farmer counts aggregated by crop and variety with K-Anonymity privacy guarantees. Excludes farmers without explicit `ANALYTICS`/`AGRISTACK_DATA_SHARE` consent or with `REVOKED` consent.
  - Query Parameters: `district: Optional[str]`
  - Response Schema: `FPOCropSummaryReport`.
- **`GET /api/v1/governed/insurance/drought-index`**:
  - Purpose: Computes block-level parametric drought risk scores combining rainfall deficits, Sentinel-2 NDWI canopy moisture indices, and CGWB groundwater levels, triggering automated insurance payout directives (`TRIGGER_PAYOUT`, `WATCH`, `NORMAL`).
  - Query Parameters: `district: Optional[str]`
  - Response Schema: `ParametricInsuranceIndexReport`.

---

## 2. Completed Milestones Summary
- **Milestone A (Foundation & Observability)**: `/health`, `/ready`, structured logging, RFC 7807 problem details.
- **Milestone B (Identity, Storage & Multi-Plot)**: Users, PBKDF2 PIN hashing, JWT tokens, DPDP consent lifecycle, audit logging, parent Farm holdings and multi-plot management.
- **Milestone C (Environmental Observations & Spatial Ingestion)**: Time-series weather observations & forecasts, Sentinel-2 spectral indices, CGWB groundwater hydrographs, and DEM terrain analysis.
- **Milestone D (Crop Knowledge Base & Soil Intelligence)**: 8 Indian staple crops taxonomy, phenological growth stages, ICAR STCR fertilizer engine, qualitative ratings, and bag conversions.
- **Milestone E (Farmer Workflows & Conversational Intelligence)**: Multi-criteria crop suitability planner, crop roadmap checkpoints, offline batch sync, proactive farmer alerts, and ICAR PoP RAG knowledge retrieval.
- **Milestone F (Scientific Evaluation, Governed Data Products & Production Hardening)**: ICAR lysimeter empirical benchmarks, plot telemetry quality & uncertainty scoring, DPDP-compliant FPO aggregation, parametric insurance drought index, sliding-window rate limiting, JWT token revocation blacklist, OWASP security headers, and Docker container orchestration.

