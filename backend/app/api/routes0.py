from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.entities import TerrainGrid, Prediction, RainfallObservation, SoilObservation, RiverObservation, ForecastObservation

router=APIRouter(prefix="/api")

@router.get("/health")
def health(): return {"status":"ok"}

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db)):
    latest=func.max(Prediction.generated_at)
    latest_time=db.scalar(select(latest))
    if latest_time is None: return {"generated_at":None,"rows":[],"kpis":{}}
    pred=(select(Prediction.grid_id,func.max(Prediction.id).label("pid"))
          .where(Prediction.generated_at==latest_time).group_by(Prediction.grid_id).subquery())
    rows=db.execute(select(Prediction,TerrainGrid).join(TerrainGrid,Prediction.grid_id==TerrainGrid.grid_id).where(Prediction.generated_at==latest_time)).all()
    out=[]
    for p,g in rows:
        out.append({"grid_id":g.grid_id,"latitude":g.latitude,"longitude":g.longitude,"elevation_m":g.elevation_m,"slope_deg":g.slope_deg,"distance_to_river_m":g.distance_to_river_m,"flood_probability":p.flood_probability,"risk_score":p.risk_score,"alert_level":p.alert_level,"explanation":p.explanation})
    counts={x:sum(1 for r in out if r["alert_level"]==x) for x in ["RED","ORANGE","YELLOW","GREEN"]}
    return {"generated_at":latest_time.isoformat(),"rows":out,"kpis":{**counts,"avg_risk":round(sum(r['risk_score'] for r in out)/len(out),2) if out else 0}}

@router.get("/grid/{grid_id}")
def grid_detail(grid_id:str,db:Session=Depends(get_db)):
    g=db.get(TerrainGrid,grid_id)
    if not g: raise HTTPException(404,"Grid not found")
    p=db.scalar(select(Prediction).where(Prediction.grid_id==grid_id).order_by(desc(Prediction.generated_at)).limit(1))
    return {"grid":{"grid_id":g.grid_id,"latitude":g.latitude,"longitude":g.longitude,"elevation_m":g.elevation_m,"slope_deg":g.slope_deg,"distance_to_river_m":g.distance_to_river_m},"prediction":None if not p else {"generated_at":p.generated_at.isoformat(),"flood_probability":p.flood_probability,"risk_score":p.risk_score,"alert_level":p.alert_level,"explanation":p.explanation}}

@router.get("/grid/{grid_id}/history")
def history(grid_id:str,db:Session=Depends(get_db)):
    rows=db.scalars(select(Prediction).where(Prediction.grid_id==grid_id).order_by(desc(Prediction.generated_at)).limit(48)).all()
    return [{"timestamp":r.generated_at.isoformat(),"risk_score":r.risk_score,"flood_probability":r.flood_probability,"alert_level":r.alert_level} for r in reversed(rows)]

@router.get("/observations/latest")
def observations(db:Session=Depends(get_db)):
    r=db.scalar(select(RainfallObservation).order_by(desc(RainfallObservation.ts)).limit(1))
    s=db.scalar(select(SoilObservation).order_by(desc(SoilObservation.ts)).limit(1))
    w=db.scalar(select(RiverObservation).order_by(desc(RiverObservation.ts)).limit(1))
    f=db.scalar(select(ForecastObservation).order_by(desc(ForecastObservation.forecast_time)).limit(1))
    return {"rainfall":None if not r else {"timestamp":r.ts.isoformat(),"rainfall_mm":r.rainfall_mm},"soil":None if not s else {"timestamp":s.ts.isoformat(),"soil_0_7":s.soil_0_7},"river":None if not w else {"timestamp":w.ts.isoformat(),"water_level_m":w.water_level_m,"gauge_height_m":w.gauge_height_m},"forecast":None if not f else {"forecast_time":f.forecast_time.isoformat(),"rainfall_mm":f.rainfall_mm}}
