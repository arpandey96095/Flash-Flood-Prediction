import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pathlib import Path
from app.db.database import Base,engine
from app.models.entities import *
Base.metadata.create_all(bind=engine)
print("PostgreSQL tables created.")
