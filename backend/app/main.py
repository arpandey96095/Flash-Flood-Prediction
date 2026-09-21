from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes1 import router
from app.config import settings

app = FastAPI(
    title="Chamoli Flash Flood Early Warning System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "Chamoli Flash Flood Early Warning System API",
        "docs": "/docs",
        "health": "/api/health"
    }