import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pathlib import Path
import pandas as pd, numpy as np, joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report,roc_auc_score,average_precision_score,confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neighbors import BallTree
from sqlalchemy import select
from app.db.database import SessionLocal
from app.models.entities import TerrainGrid,RainfallObservation,SoilObservation,RiverObservation,FloodEvent
from app.services.realtime import FEATURES

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'models'; OUT.mkdir(exist_ok=True)

def build():
 db=SessionLocal()
 try:
  r=pd.read_sql(select(RainfallObservation).order_by(RainfallObservation.ts),db.bind); s=pd.read_sql(select(SoilObservation).order_by(SoilObservation.ts),db.bind); w=pd.read_sql(select(RiverObservation).order_by(RiverObservation.ts),db.bind); g=pd.read_sql(select(TerrainGrid),db.bind); e=pd.read_sql(select(FloodEvent),db.bind)
 finally: db.close()
 r['ts']=pd.to_datetime(r.ts); s['ts']=pd.to_datetime(s.ts); w['ts']=pd.to_datetime(w.ts); e['event_date']=pd.to_datetime(e.event_date)
 # Align all dynamic modalities on rainfall's hourly clock.
 df=r.set_index('ts').sort_index(); df['rain_1h']=df.rainfall_mm; df['rain_3h']=df.rainfall_mm.rolling(3,min_periods=1).sum(); df['rain_6h']=df.rainfall_mm.rolling(6,min_periods=1).sum(); df['rain_24h']=df.rainfall_mm.rolling(24,min_periods=1).sum()
 s=s.set_index('ts').sort_index().reindex(df.index).interpolate(limit=6).ffill().bfill(); w=w.set_index('ts').sort_index().reindex(df.index).interpolate(limit=6).ffill().bfill()
 df['soil_0_7']=s.soil_0_7; df['soil_mean']=s[['soil_0_7','soil_7_28','soil_28_100','soil_100_255']].mean(axis=1); df['river_level']=w.gauge_height_m.fillna(w.water_level_m); df['river_change_6h']=df.river_level-df.river_level.shift(6); df['river_change_6h']=df.river_change_6h.fillna(0); df['month']=df.index.month; df['hour']=df.index.hour
 # Flood target: any recorded flash/river flood in next 24h. This is a district-level temporal target; spatial susceptibility is fused at inference.
 events=e.dropna(subset=['event_date']).copy(); event_days=events.event_date.dt.floor('h').tolist(); idx=df.index
 y=np.zeros(len(df),dtype=int)
 for d in event_days: y[(idx>=d-pd.Timedelta(hours=24)) & (idx<=d)]=1
 df['target']=y; df=df.replace([np.inf,-np.inf],np.nan).dropna(subset=FEATURES+['target'])
 # Keep temporal examples reasonably balanced and preserve chronology.
 pos=df[df.target==1]; neg=df[df.target==0]
 if len(pos)<10: raise RuntimeError('Too few positive hourly examples. Check flood event dates and source data.')
 neg=neg.sample(min(len(neg),len(pos)*4),random_state=42)
 temporal=pd.concat([pos,neg]).sort_index()
 # Time split: final 20% of chronological examples is test.
 cut=int(len(temporal)*0.8); tr=temporal.iloc[:cut]; te=temporal.iloc[cut:]
 # Train temporal model first. Spatial features are added through susceptibility during inference.
 Xtr=tr[FEATURES[:8]+['month','hour']]; Xte=te[FEATURES[:8]+['month','hour']]
 model=RandomForestClassifier(n_estimators=350,max_depth=14,min_samples_leaf=3,class_weight='balanced_subsample',random_state=42,n_jobs=-1)
 model.fit(Xtr,tr.target)
 prob=model.predict_proba(Xte)[:,1]
 print('Temporal test rows:',len(te),'positive:',int(te.target.sum()),'ROC-AUC:',round(roc_auc_score(te.target,prob),4) if te.target.nunique()>1 else 'NA','PR-AUC:',round(average_precision_score(te.target,prob),4))
 print(confusion_matrix(te.target,(prob>=0.5).astype(int))); print(classification_report(te.target,(prob>=0.5).astype(int),zero_division=0))
 # Bundle includes model + normalization/fusion metadata. Inference adds spatial susceptibility and static terrain features through a deterministic fusion layer.
 bundle={'model':model,'features':FEATURES[:8]+['month','hour'],'fusion':{'spatial_weight':0.25,'temporal_weight':0.75},'version':'chamoli-multimodal-flood-v1'}
 joblib.dump(bundle,OUT/'chamoli_flood_model.joblib')
 print('Saved',OUT/'chamoli_flood_model.joblib')
if __name__=='__main__': build()
