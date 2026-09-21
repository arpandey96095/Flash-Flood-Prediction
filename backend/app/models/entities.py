from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class TerrainGrid(Base):
    __tablename__="terrain_grid"
    grid_id: Mapped[str]=mapped_column(String(50), primary_key=True)
    latitude: Mapped[float]=mapped_column(Float,index=True)
    longitude: Mapped[float]=mapped_column(Float,index=True)
    elevation_m: Mapped[float|None]=mapped_column(Float)
    slope_deg: Mapped[float|None]=mapped_column(Float)
    distance_to_river_m: Mapped[float|None]=mapped_column(Float)
    susceptibility: Mapped[float]=mapped_column(Float,default=0.0)

class RainfallObservation(Base):
    __tablename__="rainfall_observations"
    ts: Mapped[datetime]=mapped_column(DateTime(timezone=False),primary_key=True)
    rainfall_mm: Mapped[float]=mapped_column(Float)

class SoilObservation(Base):
    __tablename__="soil_moisture_observations"
    ts: Mapped[datetime]=mapped_column(DateTime(timezone=False),primary_key=True)
    soil_0_7: Mapped[float|None]=mapped_column(Float)
    soil_7_28: Mapped[float|None]=mapped_column(Float)
    soil_28_100: Mapped[float|None]=mapped_column(Float)
    soil_100_255: Mapped[float|None]=mapped_column(Float)

class RiverObservation(Base):
    __tablename__="river_level_observations"
    ts: Mapped[datetime]=mapped_column(DateTime(timezone=False),primary_key=True)
    water_level_m: Mapped[float|None]=mapped_column(Float)
    gauge_height_m: Mapped[float|None]=mapped_column(Float)

class FloodEvent(Base):
    __tablename__="flood_events"
    event_id: Mapped[str]=mapped_column(String(100),primary_key=True)
    event_date: Mapped[datetime]=mapped_column(DateTime(timezone=False),index=True)
    event_end_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=False))
    event_type: Mapped[str|None]=mapped_column(String(50))
    trigger: Mapped[str|None]=mapped_column(String(100))
    severity: Mapped[str|None]=mapped_column(String(50))
    village_locality: Mapped[str|None]=mapped_column(String(250))
    latitude: Mapped[float|None]=mapped_column(Float)
    longitude: Mapped[float|None]=mapped_column(Float)

class ForecastObservation(Base):
    __tablename__="forecast_observations"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    fetched_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    forecast_time: Mapped[datetime]=mapped_column(DateTime(timezone=False),index=True)
    rainfall_mm: Mapped[float]=mapped_column(Float)
    latitude: Mapped[float]=mapped_column(Float)
    longitude: Mapped[float]=mapped_column(Float)
    source: Mapped[str]=mapped_column(String(50),default="open-meteo")

class Prediction(Base):
    __tablename__="flood_predictions"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    generated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    grid_id: Mapped[str]=mapped_column(String(50),index=True)
    horizon_hours: Mapped[int]=mapped_column(Integer)
    flood_probability: Mapped[float]=mapped_column(Float)
    risk_score: Mapped[float]=mapped_column(Float)
    alert_level: Mapped[str]=mapped_column(String(20))
    explanation: Mapped[str]=mapped_column(Text)
    model_version: Mapped[str]=mapped_column(String(100))

Index("prediction_grid_time_idx",Prediction.grid_id,Prediction.generated_at.desc())
