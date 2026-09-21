from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.database import engine
from datetime import datetime, timezone
import requests

router = APIRouter()


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Chamoli Flash Flood Early Warning API"
    }


# ============================================================
# DASHBOARD GRID DATA
# ============================================================

@router.get("/dashboard")
def get_dashboard():

    query = text("""
        SELECT
            grid_id,
            latitude,
            longitude,
            village_name,
            block_name,
            district_name,
            mapping_method,
            generated_at,
            horizon_hours,
            flood_probability,
            risk_score,
            alert_level,
            explanation,
            model_version
        FROM flood_prediction_dashboard
        ORDER BY risk_score DESC;
    """)

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    return {
        "count": len(rows),
        "data": [dict(row) for row in rows]
    }


# ============================================================
# SUMMARY
# ============================================================

@router.get("/summary")
def get_summary():

    query = text("""
        SELECT
            COUNT(*) AS total_cells,

            COUNT(*) FILTER (
                WHERE UPPER(alert_level) = 'RED'
            ) AS red_cells,

            COUNT(*) FILTER (
                WHERE UPPER(alert_level) = 'ORANGE'
            ) AS orange_cells,

            COUNT(*) FILTER (
                WHERE UPPER(alert_level) = 'YELLOW'
            ) AS yellow_cells,

            COUNT(*) FILTER (
                WHERE UPPER(alert_level) = 'GREEN'
            ) AS green_cells,

            ROUND(
                AVG(risk_score)::numeric,
                2
            ) AS average_risk,

            ROUND(
                MAX(risk_score)::numeric,
                2
            ) AS maximum_risk

        FROM flood_prediction_dashboard;
    """)

    with engine.connect() as connection:
        result = connection.execute(query).mappings().first()

    return dict(result)


# ============================================================
# VILLAGE DATA
# ============================================================

@router.get("/villages")
def get_villages():

    query = text("""
        SELECT
            village_name,
            block_name,
            district_name,

            COUNT(*) AS grid_cells,

            ROUND(
                AVG(risk_score)::numeric,
                2
            ) AS average_risk,

            ROUND(
                PERCENTILE_CONT(0.90)
                WITHIN GROUP (
                    ORDER BY risk_score
                )::numeric,
                2
            ) AS p90_risk,

            ROUND(
                MAX(risk_score)::numeric,
                2
            ) AS max_risk

        FROM flood_prediction_dashboard

        WHERE village_name IS NOT NULL
          AND LOWER(TRIM(village_name)) NOT IN (
              '',
              'none',
              'unmapped area'
          )

        GROUP BY
            village_name,
            block_name,
            district_name

        ORDER BY average_risk DESC;
    """)

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    output = []

    for row in rows:

        average_risk = float(row["average_risk"] or 0)
        p90_risk = float(row["p90_risk"] or 0)

        # Village-level operational score.
        # This prevents one extreme grid cell from making
        # the entire village RED.
        village_risk = (
            0.75 * average_risk
            +
            0.25 * p90_risk
        )

        if village_risk >= 75:
            alert = "RED"
        elif village_risk >= 55:
            alert = "ORANGE"
        elif village_risk >= 35:
            alert = "YELLOW"
        else:
            alert = "GREEN"

        output.append({
            "village_name": row["village_name"],
            "block_name": row["block_name"],
            "district_name": row["district_name"],
            "grid_cells": int(row["grid_cells"]),
            "average_risk": average_risk,
            "p90_risk": p90_risk,
            "max_risk": float(row["max_risk"] or 0),
            "village_risk": round(village_risk, 2),
            "alert_level": alert
        })

    return {
        "count": len(output),
        "data": output
    }


# ============================================================
# RISK TRENDS
# ============================================================

@router.get("/trends")
def get_trends():

    query = text("""
        SELECT
            generated_at,

            ROUND(
                AVG(risk_score)::numeric,
                2
            ) AS average_risk,

            ROUND(
                MAX(risk_score)::numeric,
                2
            ) AS maximum_risk

        FROM flood_predictions

        GROUP BY generated_at

        ORDER BY generated_at;
    """)

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    return {
        "count": len(rows),
        "data": [dict(row) for row in rows]
    }


# ============================================================
# CURRENT CONDITIONS
# ============================================================

@router.get("/conditions")
def get_conditions():

    result = {}

    # -----------------------------
    # Latest rainfall
    # -----------------------------

    try:
        query = text("""
            SELECT
                time,
                rain_mm
            FROM rainfall_observations
            ORDER BY time DESC
            LIMIT 1;
        """)

        with engine.connect() as connection:
            rainfall = connection.execute(query).mappings().first()

        if rainfall:
            result["rainfall"] = {
                "timestamp": rainfall["time"],
                "value_mm": float(rainfall["rain_mm"] or 0)
            }

    except Exception:
        result["rainfall"] = None


    # -----------------------------
    # Latest soil moisture
    # -----------------------------

    try:
        query = text("""
            SELECT
                time,
                soil_moisture_0_to_7cm,
                soil_moisture_7_to_28cm,
                soil_moisture_28_to_100cm,
                soil_moisture_100_to_255cm
            FROM soil_moisture_observations
            ORDER BY time DESC
            LIMIT 1;
        """)

        with engine.connect() as connection:
            soil = connection.execute(query).mappings().first()

        if soil:

            values = [
                soil["soil_moisture_0_to_7cm"],
                soil["soil_moisture_7_to_28cm"],
                soil["soil_moisture_28_to_100cm"],
                soil["soil_moisture_100_to_255cm"]
            ]

            values = [
                float(v)
                for v in values
                if v is not None
            ]

            result["soil_moisture"] = {
                "timestamp": soil["time"],
                "mean": (
                    sum(values) / len(values)
                    if values
                    else None
                )
            }

    except Exception:
        result["soil_moisture"] = None


    # -----------------------------
    # Latest river level
    # -----------------------------

    try:
        query = text("""
            SELECT
                timestamp,
                measured_water_level_m,
                gauge_height_above_zero_m
            FROM river_level_observations
            ORDER BY timestamp DESC
            LIMIT 1;
        """)

        with engine.connect() as connection:
            river = connection.execute(query).mappings().first()

        if river:

            value = river["gauge_height_above_zero_m"]

            if value is None:
                value = river["measured_water_level_m"]

            result["river"] = {
                "timestamp": river["timestamp"],
                "level_m": (
                    float(value)
                    if value is not None
                    else None
                )
            }

    except Exception:
        result["river"] = None


    return result


# ============================================================
# WEATHER FORECAST
# ============================================================

@router.get("/forecast")
def get_forecast():

    # Approximate central Chamoli coordinate.
    # This is used only for district-level forecast display.
    latitude = 30.40
    longitude = 79.33

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&hourly=precipitation"
        "&forecast_days=2"
        "&timezone=Asia%2FKolkata"
    )

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        hourly = data.get("hourly", {})

        times = hourly.get("time", [])
        precipitation = hourly.get(
            "precipitation",
            []
        )

        now = datetime.now(
            timezone.utc
        )

        forecast = []

        for timestamp, rain in zip(
            times,
            precipitation
        ):

            forecast.append({
                "time": timestamp,
                "precipitation_mm": float(
                    rain or 0
                )
            })

        return {
            "latitude": latitude,
            "longitude": longitude,
            "forecast": forecast
        }

    except Exception as exc:

        return {
            "error": "Unable to retrieve weather forecast",
            "details": str(exc),
            "forecast": []
        }


# ============================================================
# COMPLETE DISTRICT OVERVIEW
# ============================================================

@router.get("/overview")
def get_overview():

    # --------------------------------------------------------
    # Village risk aggregation
    # --------------------------------------------------------

    village_query = text("""
        SELECT
            village_name,
            block_name,
            district_name,

            COUNT(*) AS grid_cells,

            AVG(risk_score) AS average_risk,

            PERCENTILE_CONT(0.90)
            WITHIN GROUP (
                ORDER BY risk_score
            ) AS p90_risk,

            MAX(risk_score) AS max_risk,

            AVG(flood_probability)
            AS average_probability,

            MAX(flood_probability)
            AS max_probability

        FROM flood_prediction_dashboard

        WHERE village_name IS NOT NULL
          AND LOWER(TRIM(village_name)) NOT IN (
              '',
              'none',
              'unmapped area'
          )

        GROUP BY
            village_name,
            block_name,
            district_name;
    """)

    with engine.connect() as connection:
        village_rows = connection.execute(
            village_query
        ).mappings().all()

    villages = []

    for row in village_rows:

        avg_risk = float(
            row["average_risk"] or 0
        )

        p90_risk = float(
            row["p90_risk"] or 0
        )

        village_risk = (
            0.75 * avg_risk
            +
            0.25 * p90_risk
        )

        if village_risk >= 75:
            alert = "RED"
        elif village_risk >= 55:
            alert = "ORANGE"
        elif village_risk >= 35:
            alert = "YELLOW"
        else:
            alert = "GREEN"

        villages.append({
            "village_name": row["village_name"],
            "block_name": row["block_name"],
            "district_name": row["district_name"],
            "grid_cells": int(row["grid_cells"]),
            "average_risk": round(avg_risk, 2),
            "p90_risk": round(p90_risk, 2),
            "village_risk": round(
                village_risk,
                2
            ),
            "average_probability": round(
                float(
                    row["average_probability"]
                    or 0
                ) * 100,
                2
            ),
            "max_probability": round(
                float(
                    row["max_probability"]
                    or 0
                ) * 100,
                2
            ),
            "alert_level": alert
        })

    # --------------------------------------------------------
    # District statistics
    # --------------------------------------------------------

    total_villages = len(villages)

    red = sum(
        1 for v in villages
        if v["alert_level"] == "RED"
    )

    orange = sum(
        1 for v in villages
        if v["alert_level"] == "ORANGE"
    )

    yellow = sum(
        1 for v in villages
        if v["alert_level"] == "YELLOW"
    )

    green = sum(
        1 for v in villages
        if v["alert_level"] == "GREEN"
    )

    district_risk = (
        sum(v["village_risk"] for v in villages)
        / total_villages
        if total_villages
        else 0
    )

    max_probability = max(
        (
            v["max_probability"]
            for v in villages
        ),
        default=0
    )

    if district_risk >= 75:
        district_alert = "RED"
    elif district_risk >= 55:
        district_alert = "ORANGE"
    elif district_risk >= 35:
        district_alert = "YELLOW"
    else:
        district_alert = "GREEN"

    # --------------------------------------------------------
    # Current conditions
    # --------------------------------------------------------

    conditions = get_conditions()

    # --------------------------------------------------------
    # Weather forecast
    # --------------------------------------------------------

    weather = get_forecast()

    forecast_values = [
        item["precipitation_mm"]
        for item in weather.get(
            "forecast",
            []
        )
    ]

    forecast_24h = sum(
        forecast_values[:24]
    )

    return {
        "district": "Chamoli",

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "forecast_horizon_hours": 24,

        "district_status": {
            "risk_score": round(
                district_risk,
                2
            ),
            "alert_level": district_alert,
            "highest_modeled_probability": round(
                max_probability,
                2
            )
        },

        "villages": {
            "total": total_villages,
            "red": red,
            "orange": orange,
            "yellow": yellow,
            "green": green
        },

        "conditions": conditions,

        "forecast": {
            "next_24h_precipitation_mm":
                round(
                    forecast_24h,
                    2
                ),
            "hourly":
                weather.get(
                    "forecast",
                    []
                )
        },

        "priority_villages": sorted(
            villages,
            key=lambda x:
                x["village_risk"],
            reverse=True
        )[:20],

        "villages_data": villages
    }