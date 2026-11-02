# 🗄️ Krishi Mitra / AgriNova — Database & Schema Inventory

**Author**: Senior Backend Architect & Database Engineer  
**Audit Date**: October 30, 2026  
**Active Migration Head**: `f49b0e3b4438` (`Initial Krishi Mitra schema`)  
**Dialects Supported**: PostgreSQL + PostGIS (Production), SQLite (Testing & Local Development)  

---

## 1. Existing Relational Schema (Physical Tables)

The active database contains **7 relational tables** managed through SQLAlchemy declarative models and Alembic migrations.

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
| `device_id` | `VARCHAR(128)` | **No** | **Foreign Key** (`device_profiles.device_id`), Index | Owning device UUID |
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
| **Identity & Security** | `User`, `FarmerProfile`, `Device`, `ConsentRecord`, `AuditLog` | Multi-tenant authentication, DPDP consent tracking, security audit logging. |
| **Land Hierarchy** | `Farm` | Grouping multiple fragmented plots under a single farm holding. |
| **Environmental Observations** | `WeatherObservation`, `WeatherForecast`, `WaterSource`, `SatelliteScene`, `SatelliteObservation`, `TerrainObservation` | Storing continuous time-series telemetry rather than transient memory snapshots. |
| **Crop Knowledge** | `Crop`, `CropVariety`, `CropAgronomicParameters` | Database-backed versioned agronomic parameters replacing static Python dict. |
| **Intelligence & Evaluation** | `WaterBalanceResult`, `CropHealthResult`, `YieldEstimate`, `HazardEvent` | Persisting calculation results for verification, history, and scientific audit. |
| **Farmer Workflows** | `CropPlan`, `RoadmapCheckpoint`, `Notification`, `SyncOperation` | Enabling crop planner, milestone trackers, push notifications, and offline sync. |
| **Data Platform Governance** | `DatasetSource`, `IngestionRun` | Tracking provenance, data freshness, and ingestion quality metrics. |

