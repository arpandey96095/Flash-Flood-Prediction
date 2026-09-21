import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from datetime import datetime,timezone
import httpx
from app.config import settings
from app.db.database import SessionLocal
from app.models.entities import ForecastObservation
LAT,LON=30.40,79.55

def main():
 url=settings.open_meteo_url
 params={"latitude":LAT,"longitude":LON,"hourly":"precipitation","forecast_days":2,"timezone":"Asia/Kolkata"}
 data=httpx.get(url,params=params,timeout=30).json(); times=data['hourly']['time']; rain=data['hourly']['precipitation']; now=datetime.now(timezone.utc)
 db=SessionLocal()
 try:
  for t,p in zip(times,rain): db.add(ForecastObservation(fetched_at=now,forecast_time=datetime.fromisoformat(t),rainfall_mm=float(p or 0),latitude=LAT,longitude=LON,source='open-meteo'))
  db.commit(); print('Stored forecast hours:',len(times))
 finally: db.close()
if __name__=='__main__': main()
