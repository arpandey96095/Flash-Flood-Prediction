from pathlib import Path
import joblib
import pandas as pd
from app.config import settings

class FloodModel:
    def __init__(self):
        self.bundle=None
        p=Path(settings.model_path)
        if p.exists(): self.bundle=joblib.load(p)
    @property
    def ready(self): return self.bundle is not None
    def predict_proba(self,df:pd.DataFrame):
        if not self.bundle: raise RuntimeError("Model not trained. Run python scripts/train_model.py")
        return self.bundle["model"].predict_proba(df[self.bundle["features"]])[:,1]
    def feature_names(self): return self.bundle["features"] if self.bundle else []
model=FloodModel()
