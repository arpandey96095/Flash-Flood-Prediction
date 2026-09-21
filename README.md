# Chamoli Multimodal Flash Flood Prediction System

This version is **flash-flood only**. It does not require physical IoT sensors, MQTT, HiveMQ or Supabase.

## Architecture
Historical rainfall + soil moisture + Alaknanda river level + terrain/grid + verified flood events -> PostgreSQL/PostGIS -> feature engineering -> ML model -> 24h risk -> FastAPI -> React/Leaflet dashboard.

## Local stack
- PostgreSQL 15/16/17/18 (local)
- Python 3.10/3.11/3.12
- FastAPI + SQLAlchemy
- scikit-learn Random Forest baseline
- React + Vite + Leaflet + Recharts
- Open-Meteo for optional current forecast input

## Important scientific note
The first model is a competition-ready baseline. It uses historical flood events to create a 24-hour temporal flood target and fuses that learned temporal probability with a transparent spatial susceptibility layer. It is **not an official warning system** and must be recalibrated with operational gauge/forecast data before real-world deployment.

## VS Code quick start
1. Create PostgreSQL database `chamoli_flood` and enable PostGIS.
2. Copy `backend/.env.example` to `backend/.env` and set your PostgreSQL password.
3. Create Python venv in `backend` and install requirements.
4. Run `python scripts/init_db.py`.
5. Run `python scripts/load_data.py`.
6. Run `python scripts/train_model.py`.
7. Run `python scripts/fetch_forecast.py` (optional, for forecast storage/dashboard extension).
8. Run `python scripts/run_prediction.py`.
9. Start API: `uvicorn app.main:app --reload`.
10. In another terminal, from the repo root: `npm install`, `npm run dev`, open http://localhost:5173.

## Frontend dashboard
A dark, technical single-page dashboard (React + Vite + Leaflet + Recharts) lives at the repo root:

- **District Overview** — KPI cards (cells, mean/max risk, RED count, villages at risk), risk map, district status, alert distribution, live telemetry + 24 h Open-Meteo forecast.
- **Risk Map** — colour-coded 500 m grid cells on a dark basemap, with alert-level filters, village search and a risk threshold slider.
- **Village Watchlist** — sortable table of village-level risk with alert chips and search/alert filtering.
- **Trend Analysis** — last-48 h mean/max risk with RED/ORANGE/YELLOW reference bands.

The UI talks to the FastAPI endpoints `/api/dashboard`, `/api/summary`, `/api/villages`, `/api/trends`, `/api/conditions` (Vite dev-server proxy → :8000). If the backend or PostgreSQL is unreachable it falls back to generated demo data and shows a `DEMO DATA` badge, so the dashboard is always reviewable.

## Optional village layer
The current uploaded data contains a 500m grid, not an official village polygon layer. For the first working version the map therefore shows prediction cells. Add official Uttarakhand village boundaries later and perform a PostGIS spatial join to expose village names
