
from datetime import datetime, timezone
import httpx
from app.config import settings

async def fetch_forecasts(villages: list[dict]) -> list[dict]:
    if not villages:
        return []

    # Open-Meteo supports comma-separated coordinates. Batch to keep URLs manageable.
    result = []
    for start in range(0, len(villages), 40):
        batch = villages[start:start+40]
        lat = ",".join(str(v["latitude"]) for v in batch)
        lon = ",".join(str(v["longitude"]) for v in batch)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation,soil_moisture_0_to_7cm",
            "forecast_days": 2,
            "timezone": "UTC",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(settings.open_meteo_url, params=params)
            r.raise_for_status()
            payload = r.json()

        if isinstance(payload, dict) and "hourly" in payload:
            payload = [payload]

        now = datetime.now(timezone.utc)
        for village, item in zip(batch, payload):
            times = item["hourly"]["time"]
            precip = item["hourly"]["precipitation"]
            soil = item["hourly"].get("soil_moisture_0_to_7cm", [None]*len(times))

            future_rain = []
            future_soil = []
            for t, p, s in zip(times, precip, soil):
                dt = datetime.fromisoformat(t.replace("Z","+00:00"))
                if dt >= now:
                    future_rain.append(float(p or 0))
                    future_soil.append(float(s) if s is not None else None)

            result.append({
                "village_id": village["id"],
                "rain_next_6h_mm": sum(future_rain[:6]),
                "rain_next_24h_mm": sum(future_rain[:24]),
                "soil_forecast_mean": (
                    sum(x for x in future_soil[:24] if x is not None) /
                    max(1, len([x for x in future_soil[:24] if x is not None]))
                ),
                "source": "open-meteo",
                "ts": now,
            })
    return result
