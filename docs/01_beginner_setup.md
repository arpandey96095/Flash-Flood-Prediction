# Beginner VS Code setup

## A. PostgreSQL
Open pgAdmin -> Databases -> Create -> Database name: `chamoli_flood`.
Open Query Tool and run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

If PostgreSQL is installed locally, the connection will normally be `localhost:5432`.

## B. Backend
Open the project root in VS Code. Open a terminal:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/chamoli_flood
CORS_ORIGINS=http://localhost:5173
OPEN_METEO_URL=https://api.open-meteo.com/v1/forecast
MODEL_PATH=models/chamoli_flood_model.joblib
MODEL_VERSION=chamoli-multimodal-flood-v1
```

Then:

```powershell
python scripts/init_db.py
python scripts/load_data.py
python scripts/train_model.py
python scripts/run_prediction.py
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## C. Frontend
Open a second VS Code terminal:

```powershell
cd E:\SIH
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally http://localhost:5173.

## D. What each command does
- `init_db.py`: creates PostgreSQL tables.
- `load_data.py`: imports your rainfall, soil, river, flood-event and terrain datasets.
- `train_model.py`: builds rolling rainfall/soil/river features, creates the next-24-hour flood target, performs a chronological test split and saves the model.
- `run_prediction.py`: applies the trained model to every Chamoli 500m grid cell and writes risk predictions to PostgreSQL.
- `fetch_forecast.py`: pulls the next 48 hours of precipitation from Open-Meteo and stores it. This is optional in the first model iteration.
- FastAPI: reads predictions from PostgreSQL.
- React: renders KPIs, map, selected-grid details and trend charts.

## E. Why there is no IoT folder
The physical sensor layer is intentionally removed from this version. If you later obtain real sensors, a sensor gateway can write observations into the same PostgreSQL observation tables without changing the dashboard contract.
