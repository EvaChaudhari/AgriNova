# 🗄️ Krishi Mitra / AgriNova — Database & Schema Inventory

**Author**: Senior Backend Architect & Database Engineer  
**Audit Date**: October 30, 2026  
**Active Migration Head**: `f49b0e3b4438` (`Initial Krishi Mitra schema`)  
**Dialects Supported**: PostgreSQL + PostGIS (Production), SQLite (Testing & Local Development)  

---

## 1. Existing Relational Schema (Physical Tables)

The active database contains **28 relational tables** managed through SQLAlchemy declarative models and Alembic migrations.

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

### Table 18: `crops`
- **Model**: `Crop` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L24))
- **Purpose**: Master crop taxonomy, seasonal classification, and duration.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Crop identifier |
| `name` | `VARCHAR(80)` | **No** | **Unique**, Index | Common name (e.g. Cotton, Paddy, Wheat) |
| `scientific_name` | `VARCHAR(120)` | **No** | — | Botanical binomial name |
| `season` | `VARCHAR(32)` | **No** | — | Agricultural season (`KHARIF`, `RABI`, `ZAID`) |
| `category` | `VARCHAR(32)` | **No** | — | Category (`CEREAL`, `PULSE`, `OILSEED`, `FIBRE`, `CASH`) |
| `standard_duration_days` | `INTEGER` | **No** | Default: `120` | Reference growing duration (days) |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active taxonomy status |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 19: `crop_varieties`
- **Model**: `CropVariety` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L59))
- **Purpose**: Cultivar varieties, duration, stress tolerances, and yield potentials.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Variety identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Parent crop |
| `variety_name` | `VARCHAR(120)` | **No** | Index | Cultivar or hybrid name (e.g. Bt Cotton RCH-2) |
| `duration_days` | `INTEGER` | **No** | — | Maturity duration (days) |
| `drought_tolerance` | `VARCHAR(32)` | **No** | Default: `'MEDIUM'` | `LOW`, `MEDIUM`, `HIGH` |
| `flood_tolerance` | `VARCHAR(32)` | **No** | Default: `'LOW'` | `LOW`, `MEDIUM`, `HIGH` |
| `potential_yield_q_ha` | `FLOAT` | **No** | — | Potential maximum yield (quintals/ha) |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 20: `crop_growth_stages`
- **Model**: `CropGrowthStage` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L78))
- **Purpose**: FAO-56 phenological growth stage parameters ($K_c$, $Z_r$, $p$, $K_y$, critical water flags).

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Growth stage identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Parent crop |
| `stage_name` | `VARCHAR(64)` | **No** | — | `INITIAL`, `VEGETATIVE`, `FLOWERING`, `MATURITY` |
| `start_das` | `INTEGER` | **No** | — | Starting Day After Sowing (DAS) |
| `end_das` | `INTEGER` | **No** | — | Ending Day After Sowing (DAS) |
| `kc` | `FLOAT` | **No** | — | FAO-56 crop coefficient $K_c$ |
| `rooting_depth_m` | `FLOAT` | **No** | — | Effective rooting depth $Z_r$ (m) |
| `depletion_fraction_p` | `FLOAT` | **No** | — | Depletion fraction without water stress $p$ |
| `ky` | `FLOAT` | **No** | — | Yield response factor $K_y$ |
| `critical_water_stage` | `BOOLEAN` | **No** | Default: `False` | Drought/moisture sensitive flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 21: `crop_nutrient_benchmarks`
- **Model**: `CropNutrientBenchmark` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L104))
- **Purpose**: ICAR STCR targeted yield equation coefficients and maximum safe chemical limits.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Benchmark identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), **Unique**, Index | Associated crop |
| `stcr_a_n` | `FLOAT` | **No** | — | Target yield multiplier for N ($A_n$) |
| `stcr_b_n` | `FLOAT` | **No** | — | Soil test subtraction coefficient for N ($B_n$) |
| `stcr_a_p` | `FLOAT` | **No** | — | Target yield multiplier for P ($A_p$) |
| `stcr_b_p` | `FLOAT` | **No** | — | Soil test subtraction coefficient for P ($B_p$) |
| `stcr_a_k` | `FLOAT` | **No** | — | Target yield multiplier for K ($A_k$) |
| `stcr_b_k` | `FLOAT` | **No** | — | Soil test subtraction coefficient for K ($B_k$) |
| `max_n_kg_ha` | `FLOAT` | **No** | Default: `200.0` | ICAR safe upper bound for Nitrogen |
| `max_p_kg_ha` | `FLOAT` | **No** | Default: `100.0` | ICAR safe upper bound for Phosphorus |
| `max_k_kg_ha` | `FLOAT` | **No** | Default: `100.0` | ICAR safe upper bound for Potassium |
| `target_yield_default_q_ha` | `FLOAT` | **No** | Default: `25.0` | Standard regional target yield (q/ha) |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 22: `crop_pest_profiles`
- **Model**: `CropPestProfile` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L125))
- **Purpose**: CIB&RC approved integrated pest management (IPM) guidelines, economic threshold levels (ETL), and stage links.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Pest profile record ID |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Host crop |
| `pest_name` | `VARCHAR(160)` | **No** | Index | Pest or disease name with scientific binomial |
| `pest_type` | `VARCHAR(32)` | **No** | — | `INSECT`, `FUNGAL`, `BACTERIAL`, `VIRAL`, `WEED` |
| `affected_growth_stage` | `VARCHAR(64)` | **No** | Default: `'ALL'` | Growth stage when pest manifests |
| `symptoms` | `TEXT` | **No** | — | Visual diagnostic symptoms |
| `economic_threshold_etl` | `TEXT` | **No** | — | Action threshold (e.g. 1 larva/meter) |
| `ipm_practice` | `TEXT` | **No** | — | Biological / cultural IPM measures |
| `approved_chemical` | `TEXT` | Yes | — | CIB&RC certified pesticide active ingredient |
| `cib_restriction` | `TEXT` | Yes | — | Safety interval and application restrictions |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

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

### Table 18: `crops`
- **Model**: `Crop` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L24))
- **Purpose**: Master crop taxonomy, seasonal classification, and duration.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Crop identifier |
| `name` | `VARCHAR(80)` | **No** | **Unique**, Index | Common name (e.g. Cotton, Paddy, Wheat) |
| `scientific_name` | `VARCHAR(120)` | **No** | — | Botanical binomial name |
| `season` | `VARCHAR(32)` | **No** | — | Agricultural season (`KHARIF`, `RABI`, `ZAID`) |
| `category` | `VARCHAR(32)` | **No** | — | Category (`CEREAL`, `PULSE`, `OILSEED`, `FIBRE`, `CASH`) |
| `standard_duration_days` | `INTEGER` | **No** | Default: `120` | Reference growing duration (days) |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active taxonomy status |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 19: `crop_varieties`
- **Model**: `CropVariety` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L59))
- **Purpose**: Cultivar varieties, duration, stress tolerances, and yield potentials.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Variety identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Parent crop |
| `variety_name` | `VARCHAR(120)` | **No** | Index | Cultivar or hybrid name (e.g. Bt Cotton RCH-2) |
| `duration_days` | `INTEGER` | **No** | — | Maturity duration (days) |
| `drought_tolerance` | `VARCHAR(32)` | **No** | Default: `'MEDIUM'` | `LOW`, `MEDIUM`, `HIGH` |
| `flood_tolerance` | `VARCHAR(32)` | **No** | Default: `'LOW'` | `LOW`, `MEDIUM`, `HIGH` |
| `potential_yield_q_ha` | `FLOAT` | **No** | — | Potential maximum yield (quintals/ha) |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 20: `crop_growth_stages`
- **Model**: `CropGrowthStage` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L78))
- **Purpose**: FAO-56 phenological growth stage parameters ($K_c$, $Z_r$, $p$, $K_y$, critical water flags).

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Growth stage identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Parent crop |
| `stage_name` | `VARCHAR(64)` | **No** | — | `INITIAL`, `VEGETATIVE`, `FLOWERING`, `MATURITY` |
| `start_das` | `INTEGER` | **No** | — | Starting Day After Sowing (DAS) |
| `end_das` | `INTEGER` | **No** | — | Ending Day After Sowing (DAS) |
| `kc` | `FLOAT` | **No** | — | FAO-56 crop coefficient $K_c$ |
| `rooting_depth_m` | `FLOAT` | **No** | — | Effective rooting depth $Z_r$ (m) |
| `depletion_fraction_p` | `FLOAT` | **No** | — | Depletion fraction without water stress $p$ |
| `ky` | `FLOAT` | **No** | — | Yield response factor $K_y$ |
| `critical_water_stage` | `BOOLEAN` | **No** | Default: `False` | Drought/moisture sensitive flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 21: `crop_nutrient_benchmarks`
- **Model**: `CropNutrientBenchmark` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L104))
- **Purpose**: ICAR STCR targeted yield equation coefficients and maximum safe chemical limits.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Benchmark identifier |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), **Unique**, Index | Associated crop |
| `stcr_a_n` | `FLOAT` | **No** | — | Target yield multiplier for N ($A_n$) |
| `stcr_b_n` | `FLOAT` | **No** | — | Soil test subtraction coefficient for N ($B_n$) |
| `stcr_a_p` | `FLOAT` | **No** | — | Target yield multiplier for P ($A_p$) |
| `stcr_b_p` | `FLOAT` | **No** | — | Soil test subtraction coefficient for P ($B_p$) |
| `stcr_a_k` | `FLOAT` | **No** | — | Target yield multiplier for K ($A_k$) |
| `stcr_b_k` | `FLOAT` | **No** | — | Soil test subtraction coefficient for K ($B_k$) |
| `max_n_kg_ha` | `FLOAT` | **No** | Default: `200.0` | ICAR safe upper bound for Nitrogen |
| `max_p_kg_ha` | `FLOAT` | **No** | Default: `100.0` | ICAR safe upper bound for Phosphorus |
| `max_k_kg_ha` | `FLOAT` | **No** | Default: `100.0` | ICAR safe upper bound for Potassium |
| `target_yield_default_q_ha` | `FLOAT` | **No** | Default: `25.0` | Standard regional target yield (q/ha) |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 22: `crop_pest_profiles`
- **Model**: `CropPestProfile` ([`app/models/crop_knowledge.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/crop_knowledge.py#L125))
- **Purpose**: CIB&RC approved integrated pest management (IPM) guidelines, economic threshold levels (ETL), and stage links.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Pest profile record ID |
| `crop_id` | `INTEGER` | **No** | **Foreign Key** (`crops.id`), Index | Host crop |
| `pest_name` | `VARCHAR(160)` | **No** | Index | Pest or disease name with scientific binomial |
| `pest_type` | `VARCHAR(32)` | **No** | — | `INSECT`, `FUNGAL`, `BACTERIAL`, `VIRAL`, `WEED` |
| `affected_growth_stage` | `VARCHAR(64)` | **No** | Default: `'ALL'` | Growth stage when pest manifests |
| `symptoms` | `TEXT` | **No** | — | Visual diagnostic symptoms |
| `economic_threshold_etl` | `TEXT` | **No** | — | Action threshold (e.g. 1 larva/meter) |
| `ipm_practice` | `TEXT` | **No** | — | Biological / cultural IPM measures |
| `approved_chemical` | `TEXT` | Yes | — | CIB&RC certified pesticide active ingredient |
| `cib_restriction` | `TEXT` | Yes | — | Safety interval and application restrictions |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 23: `crop_plans`
- **Model**: `CropPlan` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L27))
- **Purpose**: Multi-criteria crop suitability rankings and farmer choices.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Crop plan evaluation ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Evaluated farm plot |
| `season` | `VARCHAR(32)` | **No** | — | Evaluated season (`KHARIF`, `RABI`, `ZAID`) |
| `target_year` | `INTEGER` | **No** | — | Crop planning calendar year |
| `rankings_json` | `TEXT` | **No** | — | Serialized candidate crops, scores, and risk tiers |
| `selected_crop` | `VARCHAR(80)` | Yes | — | Crop chosen by the farmer |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |

---

### Table 24: `crop_roadmaps`
- **Model**: `CropRoadmap` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L41))
- **Purpose**: Crop cycle timeline, duration, current stage, and milestone progress.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Roadmap record ID |
| `plot_id` | `INTEGER` | **No** | **Foreign Key** (`farm_plots.id`), Index | Associated plot |
| `crop_cycle_id` | `INTEGER` | Yes | **Foreign Key** (`crop_cycles.id`), Index | Associated active crop cycle |
| `crop_name` | `VARCHAR(80)` | **No** | — | Crop name |
| `variety_name` | `VARCHAR(120)` | Yes | — | Cultivar variety |
| `sowing_date` | `DATE` | **No** | — | Crop sowing date |
| `expected_harvest_date` | `DATE` | **No** | — | Expected physiological maturity date |
| `current_stage` | `VARCHAR(64)` | **No** | Default: `'INITIAL'` | Active phenological growth stage |
| `total_checkpoints` | `INTEGER` | **No** | Default: `6` | Total planned milestone interventions |
| `completed_checkpoints`| `INTEGER` | **No** | Default: `0` | Number of milestones completed |
| `is_active` | `BOOLEAN` | **No** | Default: `True` | Active status flag |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Creation timestamp |
| `updated_at` | `DATETIME` | **No** | OnUpdate: UTC now | Update timestamp |

---

### Table 25: `roadmap_checkpoints`
- **Model**: `RoadmapCheckpoint` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L67))
- **Purpose**: Individual stage milestone interventions, target dates, status, and farmer notes.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Checkpoint record ID |
| `roadmap_id` | `INTEGER` | **No** | **Foreign Key** (`crop_roadmaps.id`), Index | Parent roadmap |
| `stage_name` | `VARCHAR(64)` | **No** | — | `SOWING`, `BASAL_FERTILIZATION`, `WEEDING`, etc. |
| `title` | `VARCHAR(160)` | **No** | — | Milestone title |
| `description` | `TEXT` | **No** | — | Operational agronomic instructions |
| `target_day_after_sowing` | `INTEGER` | **No** | — | Target DAS |
| `target_date` | `DATE` | **No** | — | Calendar target execution date |
| `status` | `VARCHAR(32)` | **No** | Default: `'PENDING'` | `PENDING`, `COMPLETED`, `DEFERRED` |
| `completed_at` | `DATETIME` | Yes | — | Completion timestamp |
| `notes` | `TEXT` | Yes | — | Farmer field observations |
| `actionable_guidance` | `TEXT` | Yes | — | Expert advisory directive |

---

### Table 26: `offline_sync_events`
- **Model**: `OfflineSyncEvent` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L89))
- **Purpose**: Idempotent audit record tracking client-side queued mutations.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Sync event ID |
| `idempotency_key` | `VARCHAR(128)` | **No** | **Unique**, Index | Client-generated UUID idempotency key |
| `device_id` | `VARCHAR(128)` | **No** | Index | Originating hardware device |
| `action_type` | `VARCHAR(64)` | **No** | — | `CHECKPOINT_COMPLETE`, `LOG_IRRIGATION`, etc. |
| `payload_json` | `TEXT` | **No** | — | Action payload payload |
| `status` | `VARCHAR(32)` | **No** | Default: `'APPLIED'` | `APPLIED`, `DUPLICATE_SKIPPED`, `ERROR` |
| `server_timestamp` | `DATETIME` | **No** | Default: UTC now | Server processing timestamp |
| `client_timestamp` | `DATETIME` | **No** | — | Client generation timestamp |

---

### Table 27: `farmer_notifications`
- **Model**: `FarmerNotification` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L106))
- **Purpose**: Actionable hazard, irrigation, and roadmap alert notifications with read receipts.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Notification ID |
| `device_id` | `VARCHAR(128)` | **No** | Index | Recipient device UUID |
| `plot_id` | `INTEGER` | Yes | **Foreign Key** (`farm_plots.id`), Index | Subject farm parcel |
| `notification_type` | `VARCHAR(64)` | **No** | — | `WEATHER_HAZARD`, `IRRIGATION_DUE`, `ROADMAP_CHECKPOINT` |
| `priority` | `VARCHAR(32)` | **No** | Default: `'ROUTINE'` | `URGENT`, `HIGH`, `ROUTINE` |
| `title` | `VARCHAR(200)` | **No** | — | Localized headline |
| `body` | `TEXT` | **No** | — | Detailed advisory instructions |
| `language` | `VARCHAR(10)` | **No** | Default: `'hi'` | Language code (`hi`, `mr`, `te`, `en`) |
| `channel` | `VARCHAR(32)` | **No** | Default: `'IN_APP'` | `IN_APP`, `SMS`, `WHATSAPP` |
| `is_read` | `BOOLEAN` | **No** | Default: `False` | Acknowledgment status |
| `action_url` | `VARCHAR(255)` | Yes | — | Optional deep link URL |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Generation timestamp |
| `read_at` | `DATETIME` | Yes | — | Acknowledgment timestamp |

---

### Table 28: `approved_agronomic_guides`
- **Model**: `ApprovedAgronomicGuide` ([`app/models/workflows.py`](file:///Users/evariteshkumarchaudhari/Desktop/projects/AgriNova/backend/app/models/workflows.py#L129))
- **Purpose**: Vetted ICAR / SAU Package of Practices knowledge cards for RAG grounding.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | **No** | **Primary Key**, Auto-inc | Guidance card ID |
| `crop_name` | `VARCHAR(80)` | **No** | Index | Target crop name |
| `category` | `VARCHAR(64)` | **No** | — | `NUTRIENT_MANAGEMENT`, `IPM_DISEASE_PEST`, etc. |
| `stage_name` | `VARCHAR(64)` | Yes | — | Applicable phenological growth stage |
| `icar_recommendation` | `TEXT` | **No** | — | Certified agronomic recommendation text |
| `citation_source` | `VARCHAR(255)` | **No** | — | Authoritative ICAR / SAU publication citation |
| `created_at` | `DATETIME` | **No** | Default: UTC now | Ingestion timestamp |

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
| **Crop Knowledge** | *Implemented in Milestone D* (`Crop`, `CropVariety`, `CropGrowthStage`, `CropNutrientBenchmark`, `CropPestProfile`) | Database-backed versioned agronomic knowledge, varieties, FAO-56 stages, STCR equations, and IPM pest profiles. |
| **Intelligence & Evaluation** | `WaterBalanceResult`, `CropHealthResult`, `YieldEstimate`, `HazardEvent` | Persisting calculation results for verification, history, and scientific audit. |
| **Farmer Workflows** | *Implemented in Milestone E* (`CropPlan`, `CropRoadmap`, `RoadmapCheckpoint`, `OfflineSyncEvent`, `FarmerNotification`, `ApprovedAgronomicGuide`) | Crop suitability planner, stage milestone calendars, offline sync reconciliation, localized farmer notifications, and ICAR RAG cards. |
| **Data Platform Governance** | `DatasetSource`, `IngestionRun` | Tracking provenance, data freshness, and ingestion quality metrics. |

