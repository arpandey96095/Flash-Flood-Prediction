import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pathlib import Path
import pandas as pd, numpy as np
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.entities import TerrainGrid, RainfallObservation, SoilObservation, RiverObservation, FloodEvent

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def read_hourly_rain(path):
    return pd.read_csv(path, skiprows=2, names=["ts", "rainfall_mm"])

def read_hourly_soil(path):
    return pd.read_csv(
        path,
        skiprows=2,
        names=["ts", "soil_0_7", "soil_7_28", "soil_28_100", "soil_100_255"],
    )

def clean_time(df, col):
    df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
    return df.dropna(subset=[col])

def main():
    db = SessionLocal()
    try:
        # clear imported tables; predictions are cleared separately
        for cls in [
            RainfallObservation,
            SoilObservation,
            RiverObservation,
            FloodEvent,
            TerrainGrid,
        ]:
            db.query(cls).delete(synchronize_session=False)
        db.commit()

        # 1. Terrain
        t = pd.read_csv(DATA / "chamoli_static_ml_dataset.csv")
        t = t.drop_duplicates(subset=["grid_id"])
        for c in ["elevation_m", "slope_deg", "distance_to_river_m"]:
            t[c] = pd.to_numeric(t[c], errors="coerce")
        # transparent static susceptibility proxy; replace with calibrated spatial model later
        t["susceptibility"] = np.clip(
            0.55 * (t.slope_deg / 45)
            + 0.35 * np.exp(-t.distance_to_river_m / 3000)
            + 0.10,
            0,
            1,
        )
        db.bulk_save_objects([
            TerrainGrid(
                grid_id=str(r.grid_id),
                latitude=float(r.latitude),
                longitude=float(r.longitude),
                elevation_m=float(r.elevation_m),
                slope_deg=float(r.slope_deg),
                distance_to_river_m=float(r.distance_to_river_m),
                susceptibility=float(r.susceptibility),
            )
            for r in t.itertuples()
        ])

        # 2. Rain
        r = clean_time(
            read_hourly_rain(DATA / "RAINFALL Dataset from 2000-2026.csv"),
            "ts",
        )
        r["rainfall_mm"] = pd.to_numeric(r.rainfall_mm, errors="coerce")
        r = r.dropna(subset=["rainfall_mm"]).drop_duplicates(subset=["ts"])
        db.bulk_save_objects([
            RainfallObservation(
                ts=x.ts.to_pydatetime(), rainfall_mm=float(x.rainfall_mm)
            )
            for x in r.itertuples()
        ])

        # 3. Soil
        s = clean_time(
            read_hourly_soil(DATA / "soil moisture datset from 2000-2026.csv"),
            "ts",
        )
        for c in s.columns[1:]:
            s[c] = pd.to_numeric(s[c], errors="coerce")
        s = s.dropna(subset=["soil_0_7"]).drop_duplicates(subset=["ts"])
        db.bulk_save_objects([
            SoilObservation(
                ts=x.ts.to_pydatetime(),
                soil_0_7=float(x.soil_0_7),
                soil_7_28=(
                    None if pd.isna(x.soil_7_28) else float(x.soil_7_28)
                ),
                soil_28_100=(
                    None if pd.isna(x.soil_28_100) else float(x.soil_28_100)
                ),
                soil_100_255=(
                    None if pd.isna(x.soil_100_255) else float(x.soil_100_255)
                ),
            )
            for x in s.itertuples()
        ])

        # 4. River
        w = pd.read_csv(
            DATA / "Alaknanda_Joshimath_water_level_hourly_updated.csv"
        )
        w["timestamp"] = pd.to_datetime(
            w.timestamp, dayfirst=True, errors="coerce"
        )
        w = w.dropna(subset=["timestamp"])
        for c in ["measured_water_level_m", "gauge_height_above_zero_m"]:
            w[c] = pd.to_numeric(w[c], errors="coerce")
        w = w.drop_duplicates(subset=["timestamp"])
        db.bulk_save_objects([
            RiverObservation(
                ts=x.timestamp.to_pydatetime(),
                water_level_m=(
                    None
                    if pd.isna(x.measured_water_level_m)
                    else float(x.measured_water_level_m)
                ),
                gauge_height_m=(
                    None
                    if pd.isna(x.gauge_height_above_zero_m)
                    else float(x.gauge_height_above_zero_m)
                ),
            )
            for x in w.itertuples()
        ])

        # 5. Events
        e = pd.read_csv(DATA / "chamoli_flood_events_2000_2026.csv")
        e["event_date"] = pd.to_datetime(
            e.event_date, format="mixed", errors="coerce"
        )
        e["event_end_date"] = pd.to_datetime(
            e.event_end_date, format="mixed", errors="coerce"
        )
        e = e.drop_duplicates(subset=["event_id"])
        db.bulk_save_objects([
            FloodEvent(
                event_id=str(x.event_id),
                event_date=x.event_date.to_pydatetime(),
                event_end_date=(
                    None
                    if pd.isna(x.event_end_date)
                    else x.event_end_date.to_pydatetime()
                ),
                event_type=x.event_type,
                trigger=x.trigger,
                severity=x.severity,
                village_locality=x.village_locality,
                latitude=None if pd.isna(x.latitude) else float(x.latitude),
                longitude=None if pd.isna(x.longitude) else float(x.longitude),
            )
            for x in e.itertuples()
        ])

        db.commit()
        print(
            f"Loaded terrain={len(t):,}, rainfall={len(r):,}, soil={len(s):,}, river={len(w):,}, events={len(e):,}"
        )
    finally:
        db.close()

if __name__ == "__main__":
    main()