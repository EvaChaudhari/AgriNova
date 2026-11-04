# 🌾 Krishi Mitra (AgriNova) — Modern Frontend Client

A clean, voice-first digital agriculture frontend tailored for smallholder farmers, agronomists, and agricultural extension officers in India.

---

## 🌟 Key Features

1. **Deterministic Agronomic Intelligence Dashboard**:
   - **Hazard State Machine Monitor**: Live status for `NORMAL_MODE`, `STORM_FLOOD_MODE` (enforcing pesticide/fertilizer halts), and `EL_NINO_DROUGHT_MODE` (enforcing night-time drip cycles). Includes an interactive state simulator.
   - **FAO-56 Penman-Monteith Hydrology**: Real-time water balance calculation displaying status (`IRRIGATE TODAY`, `HOLD`, `DRAIN`), recommended irrigation depth in mm, reference evapotranspiration ($ET_0$), and crop $ET_c$.
   - **5-Day Root Zone Depletion Trajectory**: Interactive Chart.js graph comparing root zone depletion ($D_t$) against Readily Available Water ($RAW$).
   - **Sentinel-2 Satellite STAC Indices**: High-resolution 10m vegetation vigour ($NDVI$) and canopy moisture / water stress ($NDWI$) gauges.
   - **Soil Health Card & Groundwater Telemetry**: Calibrated Vertisol/Alfisol benchmarks (N, P, K, pH) and CGWB groundwater levels (mbgl).

2. **Multimodal Voice & Leaf Pathology Chat Receptor**:
   - **Voice-First Input**: Powered by the browser `MediaRecorder` API. Farmers can speak their query in their native tongue; audio is transmitted directly to `/api/v1/chat/receptor`.
   - **Leaf Pathology Vision**: Farmers can snap or upload a crop leaf photo with instant thumbnail preview. Adheres strictly to CIB&RC Integrated Pest Management (IPM) guidelines with safe biological dilutions (e.g., 5% Neem Seed Kernel Extract).
   - **Vernacular Audio Playback (TTS)**: Direct audio player for backend-generated base64 speech, with Web Speech API synthesis fallback.
   - **One-Tap Farmer Advisories**: Pre-configured quick prompt chips for common farm inquiries.

3. **Interactive Farm Field GIS Map**:
   - Powered by Leaflet.js with dual base layers: **High-Resolution Satellite Imagery (Esri)** and **OpenStreetMap**.
   - Renders GeoJSON farm plot polygon boundaries, calculated centroid coordinates, and geodesic surface area in hectares.
   - Displays survey numbers, khasra numbers, slope percentages, and elevation.

4. **Vernacular Multilingual Support**:
   - Instant language switching between **हिंदी (Hindi)**, **English**, **मराठी (Marathi)**, and **తెలుగు (Telugu)**.
   - All dashboard labels, metrics, alerts, and quick prompts dynamically update.

5. **Dual-Mode Connectivity (Zero-Friction Testing)**:
   - **Live Backend Mode**: Automatically connects to FastAPI endpoints on `http://localhost:8000/api/v1`.
   - **Demo Baseline Mode**: Automatically activates if the backend is offline or unstarted, allowing users to explore all maps, charts, audio recording visuals, and diagnostic features without setup hurdles.

---

## 🚀 Quickstart & How to Run

### Method 1: Using the Zero-Dependency Python Runner (Recommended)
From the repository root directory:
```bash
python run_frontend.py
```
This launches a lightweight local HTTP server and automatically opens the browser at:
`http://localhost:3000`

### Method 2: Serving Directly with the FastAPI Backend
When running the Krishi Mitra backend:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser to:
`http://localhost:8000/app`

### Method 3: Opening Directly in Any Web Browser
You can also directly double-click or open `frontend/index.html` in Chrome, Edge, Safari, or Firefox!

---

## 📂 Architecture & Directory Layout

```text
frontend/
├── index.html            # Main Single-Page Application (SPA)
├── css/
│   └── style.css         # Custom animations, voice waves & Leaflet popups
├── js/
│   ├── config.js         # API configurations, vernacular dictionaries & crops
│   ├── mockData.js       # Calibrated CGWB, IMD, and FAO-56 fallback datasets
│   ├── api.js            # Async REST client for /bootstrap, /plots, /chat
│   ├── map.js            # Leaflet GIS map with Esri satellite & plot boundaries
│   ├── chat.js           # Multimodal voice recorder, leaf preview & TTS player
│   └── app.js            # Central state controller, language engine & Chart.js
└── assets/
    └── sample_leaf.jpg   # Sample affected cotton leaf for one-tap diagnostic testing
```

---

## 🔗 Connected Backend Endpoints

- `GET /api/v1/bootstrap?device_id=...` — Synchronizes device profile, active plot, live weather, satellite STAC indices, FAO-56 water balance, and hazard state.
- `POST /api/v1/bootstrap/onboard` — Registers or updates farmer device profiles.
- `GET /api/v1/plots?device_id=...` — Lists registered farm plots with PostGIS geometry.
- `POST /api/v1/plots` — Registers new farm plot polygon boundaries and auto-derives centroid and surface area.
- `POST /api/v1/plots/{plot_id}/crop-cycle` — Sets active crop cycle (crop name, variety, sowing date, growth stage, irrigation method).
- `POST /api/v1/chat/receptor` — Unified voice, vision, and text endpoint returning ICAR scientific guidance, hazard directives, and base64 voice audio.

