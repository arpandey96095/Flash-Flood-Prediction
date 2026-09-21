from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sqlalchemy import select, desc
from app.db.database import SessionLocal
from app.models.entities import TerrainGrid,RainfallObservation,SoilObservation,RiverObservation,ForecastObservation,Prediction
from app.services.model_service import FloodModel
from app.config import settings

FEATURES=["rain_1h","rain_3h","rain_6h","rain_24h","soil_0_7","soil_mean","river_level","river_change_6h","elevation_m","slope_deg","distance_to_river_m","susceptibility","month","hour"]

def risk_level(p):
    if p>=0.75:return "RED"
    if p>=0.55:return "ORANGE"
    if p>=0.30:return "YELLOW"
    return "GREEN"

def build_current_features(db):
    r=db.scalars(select(RainfallObservation).order_by(desc(RainfallObservation.ts)).limit(25)).all(); r=list(reversed(r))
    s=db.scalar(select(SoilObservation).order_by(desc(SoilObservation.ts)).limit(1)); w=db.scalars(select(RiverObservation).order_by(desc(RiverObservation.ts)).limit(7)).all(); w=list(reversed(w))
    if not r or not s or not w:return None
    rain=[x.rainfall_mm for x in r]; wl=[x.gauge_height_m if x.gauge_height_m is not None else x.water_level_m for x in w]
    ts=r[-1].ts
    base={"rain_1h":rain[-1],"rain_3h":sum(rain[-3:]),"rain_6h":sum(rain[-6:]),"rain_24h":sum(rain),"soil_0_7":s.soil_0_7,"soil_mean":np.nanmean([s.soil_0_7,s.soil_7_28,s.soil_28_100,s.soil_100_255]),"river_level":wl[-1],"river_change_6h":wl[-1]-wl[0],"month":ts.month,"hour":ts.hour}
    return base

def recompute():
    db=SessionLocal(); model=FloodModel()
    try:
        if not model.ready: raise RuntimeError("Model file missing. Train the model first.")
        base=build_current_features(db)
        if base is None: raise RuntimeError("Not enough observations in database.")
        grids=db.scalars(select(TerrainGrid)).all(); rows=[]
        for g in grids:
            x={**base,"elevation_m":g.elevation_m,"slope_deg":g.slope_deg,"distance_to_river_m":g.distance_to_river_m,"susceptibility":g.susceptibility}
            rows.append(x)
        df=pd.DataFrame(rows); probs=model.predict_proba(df); now=datetime.now(timezone.utc)
        db.query(Prediction).filter(Prediction.generated_at==now).delete(synchronize_session=False)
        for g,p in zip(grids,probs):
            p=float(np.clip(p,0,1)); level=risk_level(p)
            reasons=[]
            if base['rain_6h']>=50: reasons.append('heavy recent rainfall')
            if base['rain_24h']>=100: reasons.append('high 24-hour rainfall')
            if base['soil_0_7']>=0.40: reasons.append('wet surface soil')
            if base['river_change_6h']>=0.25: reasons.append('rising river level')
            if g.susceptibility>=0.6: reasons.append('high spatial susceptibility')
            db.add(Prediction(generated_at=now,grid_id=g.grid_id,horizon_hours=24,flood_probability=round(p,5),risk_score=round(p*100,2),alert_level=level,explanation='; '.join(reasons) or 'conditions currently below major warning thresholds',model_version=settings.model_version))
        db.commit(); return len(grids)
    finally: db.close()
