# Chamoli Flash Flood Dashboard - Technical Overview

## 1. Project summary

This project is a full-stack early warning dashboard for Chamoli district that combines environmental data, machine learning prediction, and a web-based GIS dashboard. The application is designed to display a 24-hour flash-flood risk outlook across a spatial grid, aggregate the risk at village level, and present current weather/river conditions.

The system uses:

- React + Vite for the frontend SPA
- FastAPI for the backend API layer
- PostgreSQL/PostGIS for persistent storage
- SQLAlchemy ORM for database access
- scikit-learn Random Forest model for risk estimation
- Leaflet for map rendering and GIS-style overlays
- Recharts for trend visualization
- Open-Meteo as an optional forecast data source

The core operational idea is:

- ingest rainfall, soil moisture, river level, and historical flood event data
- create a 24-hour future flood target from verified events
- engineer temporal and environmental features
- train a Random Forest classifier
- store predictions in the database
- serve computed risk data through FastAPI endpoints
- render a dark technical dashboard to visualize grid cells, village aggregates, and trend analytics

---

## 2. High-level architecture

The repository follows a classic full-stack pattern:

- Frontend app: root-level React project under `src/`
- Backend app: `backend/app/`
- Database schema: `database/schema.sql`
- ML training pipeline: `backend/scripts/train_model.py`
- Prediction runner: `backend/scripts/run_prediction.py`
- Runtime launcher: `start_dashboard.bat`

The frontend and backend are loosely coupled through a local proxy configuration:

- Vite dev server runs on port 5173
- API calls are proxied to `http://localhost:8000`
- FastAPI runs with Uvicorn and exposes resources under `/api`

This allows the frontend to call backend endpoints without CORS issues during local development.

---

## 3. Frontend technical details

### 3.1 Stack

From `package.json`:

- React 19
- Vite 7
- Leaflet 1.9
- Recharts 3
- Lucide React icon set
- Axios is installed but the current dashboard relies on native `fetch()` in the API client layer

### 3.2 Entry and startup

The app entry is `index.html` and `src/main.jsx`.

`index.html` sets up the root mount point and loads the frontend application bundle. Vite serves this app locally with a dark-themed dashboard shell.

### 3.3 App structure

The main application logic lives in `src/App.jsx`.

Responsibilities:

- fetches the dashboard payload using `loadDashboard()`
- maintains loading and refresh state
- tracks the active navigation section
- renders overview, map, village watchlist, and trends sections
- supports demo-mode fallback when the backend is offline
- manages selected cell modal state for map interaction

### 3.4 Frontend state model

The UI aggregates a single dashboard object returned by `loadDashboard()`:

```js
{
  mode: "live" | "demo",
  cells,
  summary,
  villages,
  trends,
  conditions,
  fetchedAt,
  health
}
```

This keeps the dashboard simple and centralized while preserving a robust fallback approach.

### 3.5 API client behavior

`src/lib/api.js` is the frontend integration layer.

Key features:

- calls `/api/dashboard`, `/api/summary`, `/api/villages`, `/api/trends`, `/api/conditions`
- applies a 4-second timeout to each fetch
- parses backend payloads into a consistent dashboard shape
- falls back to generated demo data if API requests fail
- marks the app as `demo` mode when backend is unreachable

This is a deliberate resilience strategy: the dashboard remains usable even without live data.

### 3.6 Main components

#### App shell and navigation

- `src/components/Header.jsx`: top header with refresh controls and mode state
- `src/components/Sidebar.jsx`: left navigation and alert legend
- `src/components/StatCard.jsx`: metric cards for summary KPIs

#### Map panel

`src/components/MapView.jsx`

Responsibilities:

- initializes a Leaflet map centered on the Chamoli region
- renders grid cell risk markers as circle markers
- colors cells by alert state (RED, ORANGE, YELLOW, GREEN)
- supports village search, alert filtering, and min-risk threshold filtering
- fits the viewport to the visible cell cluster on first render
- draws tooltip content and cell click handling

The map uses a canvas-based layer setup and caps rendering at 3500 markers for performance when the grid is large.

#### Condition cards

`src/components/ConditionsPanel.jsx`

This panel displays:

- last hour rainfall
- current soil moisture mean
- river level measurement
- 24-hour precipitation forecast from Open-Meteo

It uses Recharts `BarChart` to visualize forecast accumulation.

#### Trends analytics

`src/components/TrendsChart.jsx`

This chart renders multi-hour risk history over the last 48 hours, comparing:

- average risk
- maximum risk

It includes reference lines at alert thresholds 35, 55, and 75.

#### Village table

`src/components/VillagesTable.jsx`

This table aggregates risk at the village level by grouping grid cells and computing:

- grid cell count
- average risk
- maximum risk
- village-level composite risk
- alert status

It supports sorting and filtering.

#### Cell detail modal

`src/components/DetailModal.jsx`

When a user clicks a map cell, a modal opens with:

- coordinates
- elevation / slope / distance to river
- risk score and flood probability
- model explanation text
- generated timestamp and model version

### 3.7 Styling and UX

Styling is managed in `src/styles.css` and uses a dark, technical dashboard aesthetic. The design is optimized for:

- monitoring status panels
- GIS map readability
- alert scale legibility
- telemetry and risk chart readability

### 3.8 Frontend configuration

`vite.config.js` configures:

- React plugin
- dev server port 5173
- proxy rule for `/api` requests to the backend on `localhost:8000`

This is essential for local development and keeps the API location transparent to the frontend code.

---

## 4. Backend technical details

### 4.1 Stack

From `backend/requirements.txt`:

- FastAPI
- Uvicorn
- SQLAlchemy
- psycopg (PostgreSQL driver)
- pydantic-settings
- httpx
- pandas / numpy / scikit-learn
- joblib
- geopandas / shapely
- python-dotenv

### 4.2 Application bootstrap

`backend/app/main.py` contains the FastAPI app factory-like setup.

Key elements:

- app title and version metadata
- CORS middleware using `settings.cors_origins`
- router inclusion with `/api` prefix
- root health endpoint

The app loads configuration from `backend/app/config.py`, which uses `pydantic-settings` and `.env` values.

### 4.3 Configuration

`backend/app/config.py` reads:

- `database_url`
- `cors_origins`
- `open_meteo_url`
- `model_path`
- `model_version`

This centralizes environment configuration and avoids hardcoded secrets in code.

### 4.4 Database layer

`backend/app/db/database.py`

This file sets up:

- PostgreSQL SQLAlchemy engine via `create_engine()`
- session factory (`SessionLocal`)
- `get_db()` dependency helper

It uses connection pooling with `pool_pre_ping=True` and message cleanup via `pool_recycle=300`.

### 4.5 ORM model entities

`backend/app/models/entities.py`

Defines the primary SQLAlchemy entities:

- `TerrainGrid`
- `RainfallObservation`
- `SoilObservation`
- `RiverObservation`
- `FloodEvent`
- `ForecastObservation`
- `Prediction`

Important fields include:

- `grid_id`, `latitude`, `longitude`
- rainfall and soil moisture sensor readings
- river water level / gauge height
- flood event metadata
- generated predictions with `risk_score`, `alert_level`, and `flood_probability`

The database schema is intentionally compact but supports GIS-like grid prediction outputs and observed environmental conditions.

---

## 5. API endpoints

The API is divided into route modules, though both expose similar endpoints.

### 5.1 Main router: `routes1.py`

This is the active route implementation used by the app. It includes:

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/summary`
- `GET /api/villages`
- `GET /api/trends`
- `GET /api/conditions`

### 5.2 Endpoint behaviors

#### `/api/dashboard`

Returns all grid cells from the latest prediction snapshot.

Fields include:

- grid id
- coordinates
- village/block/district metadata
- `generated_at`
- `horizon_hours`
- `flood_probability`
- `risk_score`
- `alert_level`
- `explanation`
- `model_version`

#### `/api/summary`

Returns aggregated counts for the entire district grid:

- total cells
- red/orange/yellow/green counts
- average risk
- maximum risk

#### `/api/villages`

Groups risk by village and computes a village-level operational score:

```python
village_risk = 0.75 * average_risk + 0.25 * p90_risk
```

This prevents one extreme grid cell from forcing a whole village into a severe alert category.

#### `/api/trends`

Reads historical prediction snapshots and returns a time series of:

- generated timestamp
- average risk
- maximum risk

#### `/api/conditions`

Returns the latest environmental observations:

- rainfall
- soil moisture
- river level
- optionally forecast data if available

This is used to show telemetry cards on the dashboard.

### 5.3 Alternative legacy router

`backend/app/api/routes.py` appears to be an earlier or alternate implementation with similar ideas but slightly different logic. It includes more village-level aggregation logic and a direct `flood_prediction_dashboard` query pattern. The current app uses `routes1.py`, while `routes.py` appears to be a legacy or backup implementation.

---

## 6. ML and prediction pipeline

### 6.1 Data sources

The model pipeline loads datasets from `backend/data/`:

- rainfall dataset
- soil moisture dataset
- river water level dataset
- historical flood event dataset
- static spatial grid dataset

These files are processed into hourly time series and event labels.

### 6.2 Training script

`backend/scripts/train_model.py` is the heart of the ML pipeline.

It does the following:

1. loads rainfall, soil, river, and event data
2. merges them into a unified hourly dataset
3. creates rolling rainfall windows
4. computes river change features
5. adds seasonal/time-of-day features
6. builds a 24-hour future flood label based on the next 24-hour event window
7. trains a RandomForestClassifier
8. evaluates thresholds using precision, recall, F1, and ROC-AUC
9. selects the warning threshold for deployment
10. saves the trained model bundle as a joblib artifact

### 6.3 Feature engineering

The final feature set includes:

- rainfall windows: 1h, 3h, 6h, 12h, 24h
- rainfall change metrics
- soil mean moisture
- river water level
- river change over 3h / 6h / 12h
- month, hour, DOY
- sine/cosine seasonal features

These features are designed to capture short-term hydrometeorological pressure, not just static susceptibility.

### 6.4 Model choice and thresholding

The model uses:

- `RandomForestClassifier`
- 400 estimators
- max depth 16
- balanced subsampling for class imbalance
- chronological train/test split

A threshold is selected using evaluation metrics to balance recall and false alarms. The code uses a target recall threshold of 0.50.

The final bundle stores:

- model object
- feature list
- threshold
- horizon hours
- model version

The trained artifact is saved to:

- `backend/models/chamoli_flood_model.joblib`
- `backend/models/training_metrics.json`

### 6.5 Spatial susceptibility concept

The README explicitly calls out that the first model is a competition-ready baseline and combines:

- temporal probability from environmental conditions
- static spatial susceptibility layer

The final dashboard also exposes a formula-like risk logic in the UI description:

```text
Random Forest (18 features) → 24 h temporal probability fused with
static spatial susceptibility (0.75 × temporal + 0.25 × spatial).
```

This is a proxy for a hybrid risk score system that combines learned temporal signal with terrain susceptibility.

---

## 7. Prediction execution and runtime flow

### 7.1 Pretrained model use

`backend/app/services/model_service.py` wraps the `joblib` model artifact and exposes:

- `ready`
- `predict_proba(df)`
- `feature_names()`

This is the python abstraction used to run prediction in operational scripts.

### 7.2 Forecast retrieval

`backend/app/services/open_meteo.py` calls the Open-Meteo API for forecast data for villages or tracked points.

It obtains hourly precipitation and soil moisture values and computes summary values such as:

- total rain in next 6 hours
- total rain in next 24 hours
- mean soil forecast value

### 7.3 Prediction script

`backend/scripts/run_prediction.py` is the operational script that:

- loads the model
- loads the latest environmental data
- prepares feature rows for each terrain grid cell
- runs prediction over the spatial grid
- computes probability and alert levels
- writes results into the database

This script is the bridge between ML training and API consumption.

---

## 8. Data model and database schema

The root-level `database/schema.sql` initializes PostGIS and sets the schema version.

The backend ORM defines the main tables:

- `terrain_grid`
- `rainfall_observations`
- `soil_moisture_observations`
- `river_level_observations`
- `flood_events`
- `forecast_observations`
- `flood_predictions`

Key database behavior:

- predictions are stored per grid cell and timestamp
- indexes are created on grid IDs and timestamps to speed range queries
- the app queries the most recent prediction snapshot for the dashboard

The system aims at a low-latency operational view rather than a complex geospatial analytics backend.

---

## 9. Dashboard behavior and UX flow

The user experience is designed as a dashboard rather than a static report:

1. Frontend loads the dashboard payload.
2. If backend is available, the dashboard shows live data.
3. If it is not available, the app loads synthetic demo data and shows a `DEMO DATA` badge.
4. The user can navigate between overview, map, village list, and trend charts.
5. Clicking map cells reveals the model explanation and original data snapshot.
6. Summary cards update live based on risk totals.

This makes the dashboard useful both for demo purposes and for real monitoring when connected to the backend.

---

## 10. Security, deployment, and operational caveats

### 10.1 Security posture

This is a local/prototype-oriented project rather than a hardened production system.

Current points to consider:

- environment variables are used for configuration
- CORS is enabled for configured origins
- no authentication or authorization layer appears in the app
- no API rate limiting or request validation beyond FastAPI defaults is evident

### 10.2 Deployment notes

`start_dashboard.bat` starts both the frontend and backend automatically for Windows-based local use.

It performs:

- frontend dependency install if absent
- Python venv creation for backend
- backend dependency install from `requirements.txt`
- launch of Vite front-end and Uvicorn backend

### 10.3 Important caveat from project docs

The README states this is a competition-ready baseline and is not an official warning system. It must be recalibrated with operational gauge/forecast data before real-world deployment.

This is important because:

- the model is trained from historical flood event labels
- the system is designed for decision-support and review rather than direct public alerting
- spatial and environmental data might need field calibration for real disaster-response use

---

## 11. Technical strengths of the project

- Modern and lightweight stack
- Clean separation between frontend, backend, and ML logic
- Strong dashboard UX for monitoring risk
- Demo fallback makes the UI resilient in offline conditions
- Use of geospatial-aware map visualization and risk aggregation
- Clear data pipeline from raw observation to decision support dashboard

---

## 12. Potential improvements

If the project were advanced beyond the current prototype, the likely next steps would be:

- add persistent PostGIS village boundary joins
- enforce user auth and role-based access
- create a proper database migration system
- add test coverage for API responses and model training logic
- add asynchronous job processing for model re-run and prediction refresh
- integrate operational hydrological gauge feeds and live sensor channels
- improve alerting thresholds with field verification and domain calibration

---

## 13. Final assessment

This repository is a compact but well-structured early-warning prototype. It combines modern web development, machine-learning risk modeling, and geospatial dashboarding into a single project that demonstrates how flood risk intelligence can be presented and interacted with in a user-friendly interface.

The strongest technical components are the modular React UI, the FastAPI backend, the database-driven monitoring architecture, and the transparent model training pipeline. The main limitations are that it is still a project-level prototype and not yet a production-grade operational warning platform.
