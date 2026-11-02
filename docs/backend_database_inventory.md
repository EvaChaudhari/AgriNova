# 🗄️ Krishi Mitra / AgriNova — Database & Schema Inventory

**Author**: Senior Backend Architect & Database Engineer  
**Audit Date**: October 30, 2026  
**Active Migration Head**: `f49b0e3b4438` (`Initial Krishi Mitra schema`)  
**Dialects Supported**: PostgreSQL + PostGIS (Production), SQLite (Testing & Local Development)  

---

## 1. Existing Relational Schema (Physical Tables)

The active database contains **17 relational tables** managed through SQLAlchemy declarative models and Alembic migrations.

### Table 1: `device_profiles`
- **Model**: `DeviceProfile` ([`app/models/profile.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/profile.py#L13))
- **Purpose**: Hardware identifier binding for smallholder farmer device.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `device_id` | `VARCHAR(128)` | **No** | **Primary Key**, Index | Unique hardware UUID / Device identifier |
| `farmer_name` | `VARCHAR(120)` | **No** | — | Farmer full name |
| `preferred_language`| `VARCHAR(10)` | **No** | Default: `'hi'` | Language code (`hi`, `te`, `mr`, `en`) |
| `phone_number` | `VARCHAR(20)` | Yes | — | Mobile contact number |
| `kisan_id` | `VARCHAR(50)` | Yes | — | Government Kisan/PM-KISAN ID |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Last update timestamp |

**Relationships**:
- One-to-Many: `plots` -> `FarmPlot.device_id` (`CASCADE`)
- One-to-Many: `chat_sessions` -> `ChatSession.device_id` (`CASCADE`)

---

### Table 2: `farm_plots`
- **Model**: `FarmPlot` ([`app/models/plot.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/plot.py#L13))
- **Purpose**: Land parcel boundary geometry, terrain slope, soil type, and spatial centroid.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Unique plot identifier |
| `farm_id` | `INTEGER` | Yes | **Foreign Key** (`farms.id`), Index | Parent farm holding |
| `user_id` | `INTEGER` | Yes | **Foreign Key** (`users.id`), Index | Registered farmer identity |
| `device_id` | `VARCHAR(128)` | Yes | **Foreign Key** (`device_profiles.device_id`), Index | Hardware device UUID |
| `name` | `VARCHAR(120)` | **No** | — | Farmer-given plot name |
| `survey_number` | `VARCHAR(64)` | Yes | — | Revenue survey number |
| `khasra_number` | `VARCHAR(64)` | Yes | — | Land revenue Khasra number |
| `boundary` | `PostGISGeometry(POLYGON, 4326)` | **No** | Spatial Type | WGS84 closed polygon |
| `centroid_lat` | `FLOAT` | **No** | — | Centroid latitude (decimal degrees) |
| `centroid_lon` | `FLOAT` | **No** | — | Centroid longitude (decimal degrees) |
| `area_hectares` | `FLOAT` | **No** | — | Physical ground surface area (ha) |
| `soil_texture` | `VARCHAR(64)` | **No** | Default: `'Vertisol'` | Major soil type (Vertisol, Alfisol, etc.) |
| `elevation_m` | `FLOAT` | **No** | Default: `250.0` | Elevation above mean sea level (m) |
| `slope_percent` | `FLOAT` | **No** | Default: `1.5` | Terrain DEM slope (%) |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active management flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Registration timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

**Relationships**:
- Many-to-One: `farm` -> `Farm`
- Many-to-One: `device` -> `DeviceProfile`
- One-to-Many: `crop_cycles` -> `CropCycle.plot_id` (`CASCADE`)
- One-to-Many: `groundwater_observations` -> `GroundwaterObservation.plot_id` (`CASCADE`)
- One-to-Many: `soil_health_records` -> `SoilHealthRecord.plot_id` (`CASCADE`)

---

### Table 3: `crop_cycles`
- **Model**: `CropCycle` ([`app/models/plot.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/plot.py#L44))
- **Purpose**: Seasonal crop cycle tracking, growth stage, and irrigation method.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Unique crop cycle identifier |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Target plot |
| `crop_name` | `VARCHAR(80)` | **No** | — | Primary crop (Cotton, Paddy, Maize, etc.) |
| `variety` | `VARCHAR(80)` | Yes | — | Seed variety / hybrid name |
| `sowing_date` | `DATE` | **No** | Default: `today` | Date of sowing |
| `growth_stage` | `VARCHAR(32)` | **No** | Default: `'INITIAL'` | `INITIAL`, `VEGETATIVE`, `FLOWERING`, `MATURITY` |
| `irrigation_method`| `VARCHAR(32)` | **No** | Default: `'DRIP'` | `DRIP` (0.90), `SPRINKLER` (0.75), `FLOOD` (0.60) |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active in-field crop flag |
| `expected_harvest_date`| `DATE` | Yes | — | Target harvest date |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

---

### Table 4: `groundwater_observations`
- **Model**: `GroundwaterObservation` ([`app/models/telemetry.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/telemetry.py#L13))
- **Purpose**: Physical water table depth telemetry in meters below ground level (`mbgl`).

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Observation identifier |
| `plot_id` | `INTEGER` | Yes | **Foreign Key** (`farm_plots.id`), Index | Associated plot (if applicable) |
| `depth_mbgl` | `FLOAT` | **No** | — | Water table depth (m below ground level) |
| `source_type` | `VARCHAR(32)` | **No** | Default: `'FALLBACK_DISTRICT'` | `HARDWARE_SENSOR`, `INDIA_WRIS`, `FALLBACK_DISTRICT` |
| `observation_date` | `DATETIME` | **No** | Default: UTC now | Date/time of measurement |
| `created_at` | `DATETIME` | **No** | Default: UTC now | System ingestion timestamp |

---

### Table 5: `soil_health_records`
- **Model**: `SoilHealthRecord` ([`app/models/telemetry.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/telemetry.py#L26))
- **Purpose**: Soil Health Card physicochemical nutrients and acidity.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Record identifier |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Target plot |
| `nitrogen_kg_ha` | `FLOAT` | **No** | — | Available Nitrogen (kg/ha) |
| `phosphorus_kg_ha` | `FLOAT` | **No** | — | Available Phosphorus ($P_2O_5$, kg/ha) |
| `potassium_kg_ha` | `FLOAT` | **No** | — | Available Potassium ($K_2O$, kg/ha) |
| `ph` | `FLOAT` | **No** | — | Soil pH value |
| `organic_carbon_percent` | `FLOAT` | **No** | — | Soil Organic Carbon (%) |
| `source_type` | `VARCHAR(32)` | **No** | Default: `'REGIONAL_FALLBACK'` | `SOIL_HEALTH_CARD_API`, `LAB_TEST`, `REGIONAL_FALLBACK` |
| `tested_date` | `DATE` | **No** | Default: `today` | Soil test date |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 6: `chat_sessions`
- **Model**: `ChatSession` ([`app/models/chat.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/chat.py#L14))
- **Purpose**: Conversational session grouping multi-turn voice/text consultations.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `VARCHAR(36)` | **No** | **Primary Key** | UUID string identifier |
| `device_id` | `VARCHAR(128)` | **No** | **Foreign Key** (`device_profiles.device_id`), Index | Owning device |
| `plot_id` | `INTEGER` | Yes | **Foreign Key** (`farm_plots.id`) | Optional focused plot |
| `title` | `VARCHAR(200)` | Yes | Default: `'Agricultural Consultation'` | Conversation title |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

**Relationships**:
- One-to-Many: `messages` -> `ChatMessage.session_id` (`CASCADE`)

---

### Table 7: `chat_messages`
- **Model**: `ChatMessage` ([`app/models/chat.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/chat.py#L33))
- **Purpose**: Individual query and response turn with snapshot of agricultural context.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Message identifier |
| `session_id` | `VARCHAR(36)` | **No** | **Foreign Key** (`chat_sessions.id`), Index | Parent session UUID |
| `sender` | `VARCHAR(20)` | **No** | — | `USER`, `ASSISTANT`, `SYSTEM` |
| `query_text` | `TEXT` | **No** | — | Raw transcribed query |
| `response_text` | `TEXT` | Yes | — | Generated grounded advisory |
| `audio_url` | `VARCHAR(255)`| Yes | — | Synthesized audio Data URL reference |
| `image_url` | `VARCHAR(255)`| Yes | — | Uploaded leaf photo path |
| `system_context_snapshot` | `JSON` | Yes | — | Complete live context at query time |
| `hazard_state` | `VARCHAR(32)` | Yes | — | Active hazard mode at query time |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Turn timestamp |

---

### Table 8: `users`
- **Model**: `User` ([`app/models/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/auth.py#L13))
- **Purpose**: Registered farmer profile with encrypted PIN and multi-device association.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Unique user ID |
| `phone_number` | `VARCHAR(20)` | **No** | **Unique**, Index | Mobile contact number |
| `full_name` | `VARCHAR(120)` | **No** | — | Farmer full name |
| `hashed_pin` | `VARCHAR(256)` | **No** | — | PBKDF2-HMAC-SHA256 salted PIN hash |
| `preferred_language`| `VARCHAR(10)` | **No** | Default: `'hi'` | Language code (`hi`, `te`, `mr`, `en`) |
| `kisan_id` | `VARCHAR(50)` | Yes | — | Government PM-KISAN ID |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active farmer status |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Registration timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

---

### Table 13: `weather_observations`
- **Model**: `WeatherObservation` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L25))
- **Purpose**: Historical meteorological time-series records per plot.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Observation record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Monitored field plot |
| `observation_time` | `DATETIME` | **No** | Index | Timestamp of weather event |
| `temp_min_c` | `FLOAT` | **No** | — | Minimum temperature (°C) |
| `temp_max_c` | `FLOAT` | **No** | — | Maximum temperature (°C) |
| `temp_mean_c` | `FLOAT` | **No** | — | Mean temperature (°C) |
| `relative_humidity_percent` | `FLOAT` | **No** | — | Relative humidity (%) |
| `wind_speed_2m_mps` | `FLOAT` | **No** | Default: `2.0` | Wind speed at 2m (m/s) |
| `solar_radiation_mj_m2` | `FLOAT` | **No** | Default: `18.0` | Solar radiation (MJ/m²) |
| `rainfall_24h_mm` | `FLOAT` | **No** | Default: `0.0` | 24-hour precipitation (mm) |
| `source` | `VARCHAR(64)` | **No** | — | `OPENWEATHERMAP`, `IMD`, `SYNTHETIC_FALLBACK` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `MEASURED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Data confidence score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 14: `weather_forecasts`
- **Model**: `WeatherForecast` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L48))
- **Purpose**: Multi-day rolling meteorological forecast window with precipitation probabilities.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Forecast record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Target plot |
| `forecast_issued_at`| `DATETIME` | **No** | — | Forecast generation timestamp |
| `forecast_date` | `DATE` | **No** | Index | Target forecast calendar date |
| `temp_min_c` | `FLOAT` | **No** | — | Projected min temperature (°C) |
| `temp_max_c` | `FLOAT` | **No** | — | Projected max temperature (°C) |
| `rainfall_mm` | `FLOAT` | **No** | Default: `0.0` | Forecasted rainfall (mm) |
| `precipitation_probability` | `FLOAT` | **No** | Default: `0.0` | Probability of precipitation (%) |
| `condition_code` | `VARCHAR(32)` | **No** | — | Weather condition category |
| `condition_description` | `VARCHAR(120)` | **No** | — | Condition summary text |
| `source` | `VARCHAR(64)` | **No** | — | Forecast data provider |
| `provenance_type` | `VARCHAR(32)` | **No** | Default: `'FORECAST'` | Provenance indicator |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 15: `satellite_observations`
- **Model**: `SatelliteObservation` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L71))
- **Purpose**: Sentinel-2 optical spectral indices, cloud scores, and zonal statistics.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Satellite observation ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Observed field plot |
| `acquisition_date` | `DATE` | **No** | Index | Scene acquisition date |
| `stac_item_id` | `VARCHAR(128)` | Yes | — | STAC catalog scene identifier |
| `cloud_cover_percent` | `FLOAT` | **No** | Default: `0.0` | Cloud occlusion percentage over plot |
| `mean_ndvi` | `FLOAT` | **No** | — | Zonal mean NDVI [-1.0, 1.0] |
| `mean_ndwi` | `FLOAT` | **No** | — | Zonal mean NDWI [-1.0, 1.0] |
| `mean_ndmi` | `FLOAT` | Yes | — | Zonal mean NDMI [-1.0, 1.0] |
| `min_ndvi` | `FLOAT` | Yes | — | Minimum field NDVI |
| `max_ndvi` | `FLOAT` | Yes | — | Maximum field NDVI |
| `std_ndvi` | `FLOAT` | Yes | — | Standard deviation of NDVI |
| `pixel_validity_count`| `INTEGER` | **No** | Default: `1` | Number of unmasked cloud-free pixels |
| `status` | `VARCHAR(32)` | **No** | — | `MEASURED`, `CLOUD_OCCLUDED`, `SYNTHETIC_FALLBACK` |
| `source` | `VARCHAR(64)` | **No** | — | `SENTINEL_2_L2A`, `SYNTHETIC_PHENOLOGY_MODEL` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `DERIVED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Observation quality score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 16: `groundwater_time_series`
- **Model**: `GroundwaterTimeSeries` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L101))
- **Purpose**: India-WRIS / CGWB hydrograph time-series and 5-year depletion trends.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Associated plot |
| `station_id` | `VARCHAR(64)` | Yes | Index | Hydrograph station code |
| `station_name` | `VARCHAR(120)` | Yes | — | Station name |
| `record_date` | `DATE` | **No** | Index | Date of depth record |
| `depth_mbgl` | `FLOAT` | **No** | — | Depth to water table (mbgl) |
| `season_flag` | `VARCHAR(32)` | **No** | — | `PRE_MONSOON`, `POST_MONSOON`, `RABI`, `KHARIF` |
| `five_year_decline_rate_m_yr` | `FLOAT` | Yes | — | 5-year water table trend (m/year) |
| `distance_km` | `FLOAT` | Yes | — | Distance from plot centroid (km) |
| `source` | `VARCHAR(64)` | **No** | — | `INDIA_WRIS`, `CGWB`, `FALLBACK_DISTRICT` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `MEASURED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Quality confidence score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 17: `terrain_topography`
- **Model**: `TerrainTopography` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L129))
- **Purpose**: DEM slope, Topographic Wetness Index (TWI), and erosion hazard classification.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), **Unique**, Index | Field plot |
| `elevation_m` | `FLOAT` | **No** | Default: `250.0` | Elevation above MSL (m) |
| `slope_percent` | `FLOAT` | **No** | Default: `1.5` | Terrain slope percentage (%) |
| `slope_degrees` | `FLOAT` | **No** | Default: `0.86` | Terrain slope angle (degrees) |
| `aspect_degrees`| `FLOAT` | Yes | — | Aspect orientation |
| `twi` | `FLOAT` | **No** | Default: `6.5` | Topographic Wetness Index |
| `erosion_hazard`| `VARCHAR(64)` | **No** | Default: `'STABLE'` | `HIGH_EROSION_RISK`, `WATERLOGGING_SUSCEPTIBLE`, `STABLE` |
| `actionable_directive` | `VARCHAR(255)` | Yes | — | In-field agronomic soil directive |
| `source` | `VARCHAR(64)` | **No** | — | `SRTM_DEM`, `COPERNICUS_DEM`, `HYPSOMETRIC_FALLBACK` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `DERIVED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Model confidence score |
| `calculated_at` | `DATETIME` | **No** | Default: UTC now | Calculation timestamp |

---

### Table 9: `devices`
- **Model**: `Device` ([`app/models/auth.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/auth.py#L38))
- **Purpose**: Hardware device tracking, app installation version, and active session binding.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Unique device record ID |
| `device_id` | `VARCHAR(128)` | **No** | **Unique**, Index | Hardware UUID / Client device identifier |
| `user_id` | `INTEGER` | Yes | **Foreign Key** (`users.id`), Index | Bound farmer user |
| `device_model` | `VARCHAR(120)` | Yes | — | Hardware device model |
| `os_version` | `VARCHAR(64)` | Yes | — | Mobile operating system version |
| `app_version` | `VARCHAR(64)` | Yes | — | Mobile application version |
| `last_active_at` | `DATETIME` | **No** | OnUpdate: UTC now | Last active session timestamp |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active session flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Registration timestamp |

---

### Table 10: `consent_records`
- **Model**: `ConsentRecord` ([`app/models/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/consent.py#L13))
- **Purpose**: DPDP-compliant explicit farmer consent tracking for telemetry and external data sharing.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Unique consent record ID |
| `user_id` | `INTEGER` | Yes | **Foreign Key** (`users.id`), Index | Farmer user |
| `device_id` | `VARCHAR(128)` | Yes | Index | Device context |
| `purpose` | `VARCHAR(64)` | **No** | — | `IRRIGATION_ADVISORY`, `WEATHER_ALERTS`, etc. |
| `status` | `VARCHAR(20)` | **No** | Default: `'GRANTED'` | `GRANTED`, `REVOKED`, `EXPIRED` |
| `granted_at` | `DATETIME` | **No** | Default: UTC now | Consent grant timestamp |
| `revoked_at` | `DATETIME` | Yes | — | Consent revocation timestamp |
| `ip_address` | `VARCHAR(45)` | Yes | — | Client IP address |
| `user_agent` | `VARCHAR(255)` | Yes | — | Client User-Agent string |

---

### Table 11: `audit_logs`
- **Model**: `AuditLog` ([`app/models/consent.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/consent.py#L32))
- **Purpose**: Immutable append-only audit trail recording identity, consent, and lifecycle operations.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Audit record ID |
| `user_id` | `INTEGER` | Yes | **Foreign Key** (`users.id`), Index | Farmer user |
| `device_id` | `VARCHAR(128)` | Yes | Index | Device identifier |
| `action` | `VARCHAR(64)` | **No** | — | `USER_REGISTERED`, `LOGIN_SUCCESS`, `CONSENT_GRANTED`, etc. |
| `resource_type` | `VARCHAR(64)` | **No** | — | `user`, `device`, `consent`, `farm`, `plot` |
| `resource_id` | `VARCHAR(64)` | Yes | — | Identifier of affected resource |
| `details` | `VARCHAR(1000)`| Yes | — | Structured JSON or summary details |
| `ip_address` | `VARCHAR(45)` | Yes | — | Request IP address |
| `timestamp` | `DATETIME` | **No** | Default: UTC now | Immutable event timestamp |

---

### Table 12: `farms`
- **Model**: `Farm` ([`app/models/plot.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/plot.py#L14))
- **Purpose**: Parent agricultural holding aggregating multiple contiguous or fragmented plots.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Farm holding ID |
| `user_id` | `INTEGER` | Yes | **Foreign Key** (`users.id`), Index | Farmer owner |
| `device_id` | `VARCHAR(128)` | Yes | **Foreign Key** (`device_profiles.device_id`), Index | Hardware device UUID |
| `name` | `VARCHAR(120)` | **No** | — | Farm name |
| `village` | `VARCHAR(120)` | Yes | — | Village name |
| `subdistrict` | `VARCHAR(120)` | Yes | — | Subdistrict / Tehsil |
| `district` | `VARCHAR(120)` | Yes | — | District name |
| `state` | `VARCHAR(120)` | Yes | — | State name |
| `total_area_hectares`| `FLOAT` | **No** | Default: `0.0` | Aggregated active plots acreage (ha) |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active status flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Registration timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

---

### Table 13: `weather_observations`
- **Model**: `WeatherObservation` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L25))
- **Purpose**: Historical meteorological time-series records per plot.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Observation record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Monitored field plot |
| `observation_time` | `DATETIME` | **No** | Index | Timestamp of weather event |
| `temp_min_c` | `FLOAT` | **No** | — | Minimum temperature (°C) |
| `temp_max_c` | `FLOAT` | **No** | — | Maximum temperature (°C) |
| `temp_mean_c` | `FLOAT` | **No** | — | Mean temperature (°C) |
| `relative_humidity_percent` | `FLOAT` | **No** | — | Relative humidity (%) |
| `wind_speed_2m_mps` | `FLOAT` | **No** | Default: `2.0` | Wind speed at 2m (m/s) |
| `solar_radiation_mj_m2` | `FLOAT` | **No** | Default: `18.0` | Solar radiation (MJ/m²) |
| `rainfall_24h_mm` | `FLOAT` | **No** | Default: `0.0` | 24-hour precipitation (mm) |
| `source` | `VARCHAR(64)` | **No** | — | `OPENWEATHERMAP`, `IMD`, `SYNTHETIC_FALLBACK` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `MEASURED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Data confidence score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 14: `weather_forecasts`
- **Model**: `WeatherForecast` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L48))
- **Purpose**: Multi-day rolling meteorological forecast window with precipitation probabilities.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Forecast record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Target plot |
| `forecast_issued_at`| `DATETIME` | **No** | — | Forecast generation timestamp |
| `forecast_date` | `DATE` | **No** | Index | Target forecast calendar date |
| `temp_min_c` | `FLOAT` | **No** | — | Projected min temperature (°C) |
| `temp_max_c` | `FLOAT` | **No** | — | Projected max temperature (°C) |
| `rainfall_mm` | `FLOAT` | **No** | Default: `0.0` | Forecasted rainfall (mm) |
| `precipitation_probability` | `FLOAT` | **No** | Default: `0.0` | Probability of precipitation (%) |
| `condition_code` | `VARCHAR(32)` | **No** | — | Weather condition category |
| `condition_description` | `VARCHAR(120)` | **No** | — | Condition summary text |
| `source` | `VARCHAR(64)` | **No** | — | Forecast data provider |
| `provenance_type` | `VARCHAR(32)` | **No** | Default: `'FORECAST'` | Provenance indicator |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 15: `satellite_observations`
- **Model**: `SatelliteObservation` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L71))
- **Purpose**: Sentinel-2 optical spectral indices, cloud scores, and zonal statistics.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Satellite observation ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Observed field plot |
| `acquisition_date` | `DATE` | **No** | Index | Scene acquisition date |
| `stac_item_id` | `VARCHAR(128)` | Yes | — | STAC catalog scene identifier |
| `cloud_cover_percent` | `FLOAT` | **No** | Default: `0.0` | Cloud occlusion percentage over plot |
| `mean_ndvi` | `FLOAT` | **No** | — | Zonal mean NDVI [-1.0, 1.0] |
| `mean_ndwi` | `FLOAT` | **No** | — | Zonal mean NDWI [-1.0, 1.0] |
| `mean_ndmi` | `FLOAT` | Yes | — | Zonal mean NDMI [-1.0, 1.0] |
| `min_ndvi` | `FLOAT` | Yes | — | Minimum field NDVI |
| `max_ndvi` | `FLOAT` | Yes | — | Maximum field NDVI |
| `std_ndvi` | `FLOAT` | Yes | — | Standard deviation of NDVI |
| `pixel_validity_count`| `INTEGER` | **No** | Default: `1` | Number of unmasked cloud-free pixels |
| `status` | `VARCHAR(32)` | **No** | — | `MEASURED`, `CLOUD_OCCLUDED`, `SYNTHETIC_FALLBACK` |
| `source` | `VARCHAR(64)` | **No** | — | `SENTINEL_2_L2A`, `SYNTHETIC_PHENOLOGY_MODEL` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `DERIVED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Observation quality score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 16: `groundwater_time_series`
- **Model**: `GroundwaterTimeSeries` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L101))
- **Purpose**: India-WRIS / CGWB hydrograph time-series and 5-year depletion trends.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Associated plot |
| `station_id` | `VARCHAR(64)` | Yes | Index | Hydrograph station code |
| `station_name` | `VARCHAR(120)` | Yes | — | Station name |
| `record_date` | `DATE` | **No** | Index | Date of depth record |
| `depth_mbgl` | `FLOAT` | **No** | — | Depth to water table (mbgl) |
| `season_flag` | `VARCHAR(32)` | **No** | — | `PRE_MONSOON`, `POST_MONSOON`, `RABI`, `KHARIF` |
| `five_year_decline_rate_m_yr` | `FLOAT` | Yes | — | 5-year water table trend (m/year) |
| `distance_km` | `FLOAT` | Yes | — | Distance from plot centroid (km) |
| `source` | `VARCHAR(64)` | **No** | — | `INDIA_WRIS`, `CGWB`, `FALLBACK_DISTRICT` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `MEASURED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Quality confidence score |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

---

### Table 17: `terrain_topography`
- **Model**: `TerrainTopography` ([`app/models/observations.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/observations.py#L129))
- **Purpose**: DEM slope, Topographic Wetness Index (TWI), and erosion hazard classification.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), **Unique**, Index | Field plot |
| `elevation_m` | `FLOAT` | **No** | Default: `250.0` | Elevation above MSL (m) |
| `slope_percent` | `FLOAT` | **No** | Default: `1.5` | Terrain slope percentage (%) |
| `slope_degrees` | `FLOAT` | **No** | Default: `0.86` | Terrain slope angle (degrees) |
| `aspect_degrees`| `FLOAT` | Yes | — | Aspect orientation |
| `twi` | `FLOAT` | **No** | Default: `6.5` | Topographic Wetness Index |
| `erosion_hazard`| `VARCHAR(64)` | **No** | Default: `'STABLE'` | `HIGH_EROSION_RISK`, `WATERLOGGING_SUSCEPTIBLE`, `STABLE` |
| `actionable_directive` | `VARCHAR(255)` | Yes | — | In-field agronomic soil directive |
| `source` | `VARCHAR(64)` | **No** | — | `SRTM_DEM`, `COPERNICUS_DEM`, `HYPSOMETRIC_FALLBACK` |
| `provenance_type` | `VARCHAR(32)` | **No** | — | `DERIVED`, `SYNTHETIC_FALLBACK` |
| `quality_score` | `FLOAT` | **No** | Default: `1.0` | Model confidence score |
| `calculated_at` | `DATETIME` | **No** | Default: UTC now | Calculation timestamp |

---

## 2. Dialect Portability: `PostGISGeometry` TypeDecorator

To enable seamless testing without requiring local PostGIS or SpatiaLite C-libraries, [`app/core/database.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/core/database.py#L34) implements a custom TypeDecorator:

```python
class PostGISGeometry(TypeDecorator):
    impl = Geometry
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect is not None and dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(self.geom_type, srid=self.srid))
        return dialect.type_descriptor(Text())
```

- **In PostgreSQL**: Generates native PostGIS column `GEOMETRY(Polygon, 4326)`. Can leverage PostGIS `ST_Area`, `ST_Centroid`, `ST_Contains`.
- **In SQLite**: Generates `TEXT` column storing WKT strings (e.g. `POLYGON((...))`). Coordinates are parsed and evaluated via Shapely in Python.

---

## 3. Database Schema Gaps (Target Missing Entities)

The target enterprise architecture mandates 22 additional logical entities:

| Domain | Missing Entity Models | Purpose |
|---|---|---|
| **Identity & Security** | *Implemented in Milestone B* (`User`, `Device`, `ConsentRecord`, `AuditLog`) | Multi-tenant authentication, DPDP consent tracking, security audit logging. |
| **Land Hierarchy** | *Implemented in Milestone B* (`Farm`) | Grouping multiple fragmented plots under a single farm holding. |
| **Environmental Observations** | *Implemented in Milestone C* (`WeatherObservation`, `WeatherForecast`, `SatelliteObservation`, `GroundwaterTimeSeries`, `TerrainTopography`) | Storing continuous time-series telemetry and spatial terrain metrics. |
| **Crop Knowledge** | `Crop`, `CropVariety`, `CropAgronomicParameters` | Database-backed versioned agronomic parameters replacing static Python dict. |
| **Intelligence & Evaluation** | `WaterBalanceResult`, `CropHealthResult`, `YieldEstimate`, `HazardEvent` | Persisting calculation results for verification, history, and scientific audit. |
| **Farmer Workflows** | `CropPlan`, `RoadmapCheckpoint`, `Notification`, `SyncOperation` | Enabling crop planner, milestone trackers, push notifications, and offline sync. |
| **Data Platform Governance** | `DatasetSource`, `IngestionRun` | Tracking provenance, data freshness, and ingestion quality metrics. |

