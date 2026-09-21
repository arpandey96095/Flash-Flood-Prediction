from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    cors_origins: str = "http://localhost:5173"
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    model_path: str = "models/chamoli_flood_model.joblib"
    model_version: str = "chamoli-multimodal-flood-v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
