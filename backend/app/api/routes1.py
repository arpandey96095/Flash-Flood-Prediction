from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.database import engine

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Chamoli Flash Flood Early Warning API"
    }


@router.get("/dashboard")
def get_dashboard():
    query = text("""
        SELECT
            p.grid_id,
            t.latitude,
            t.longitude,
            NULL AS village_name,
            NULL AS block_name,
            NULL AS district_name,
            NULL AS mapping_method,
            generated_at,
            horizon_hours,
            flood_probability,
            risk_score,
            alert_level,
            explanation,
            model_version
        FROM flood_predictions AS p
        JOIN terrain_grid AS t ON t.grid_id = p.grid_id
        WHERE p.generated_at = (SELECT MAX(generated_at) FROM flood_predictions)
        ORDER BY p.risk_score DESC;
    """)

    try:
        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()

        return {
            "count": len(rows),
            "data": [dict(row) for row in rows]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


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

            ROUND(AVG(risk_score)::numeric, 2) AS average_risk,

            ROUND(MAX(risk_score)::numeric, 2) AS maximum_risk

        FROM flood_predictions
        WHERE generated_at = (SELECT MAX(generated_at) FROM flood_predictions);
    """)

    try:
        with engine.connect() as connection:
            result = connection.execute(query).mappings().first()

        return dict(result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@router.get("/villages")
def get_villages():
    # Village boundaries are not part of the current imported schema yet.
    return {"count": 0, "data": []}


@router.get("/trends")
def get_trends():

    query = text("""
        SELECT
            generated_at,
            ROUND(AVG(risk_score)::numeric, 2) AS average_risk,
            ROUND(MAX(risk_score)::numeric, 2) AS maximum_risk
        FROM flood_predictions
        GROUP BY generated_at
        ORDER BY generated_at;
    """)

    try:
        with engine.connect() as connection:
            rows = connection.execute(query).mappings().all()

        return {
            "count": len(rows),
            "data": [dict(row) for row in rows]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@router.get("/conditions")
def get_conditions():
    result = {"rainfall": None, "soil_moisture": None, "river": None}

    try:
        query = text("""
            SELECT ts, rainfall_mm
            FROM rainfall_observations
            ORDER BY ts DESC
            LIMIT 1;
        """)
        with engine.connect() as connection:
            row = connection.execute(query).mappings().first()
        if row:
            result["rainfall"] = {
                "timestamp": row["ts"],
                "value_mm": float(row["rainfall_mm"] or 0),
            }
    except Exception:
        pass

    try:
        query = text("""
            SELECT ts, soil_0_7, soil_7_28, soil_28_100, soil_100_255
            FROM soil_moisture_observations
            ORDER BY ts DESC
            LIMIT 1;
        """)
        with engine.connect() as connection:
            row = connection.execute(query).mappings().first()
        if row:
            values = [row[key] for key in ("soil_0_7", "soil_7_28", "soil_28_100", "soil_100_255") if row[key] is not None]
            result["soil_moisture"] = {
                "timestamp": row["ts"],
                "mean": sum(float(value) for value in values) / len(values) if values else None,
            }
    except Exception:
        pass

    try:
        query = text("""
            SELECT ts, water_level_m, gauge_height_m
            FROM river_level_observations
            ORDER BY ts DESC
            LIMIT 1;
        """)
        with engine.connect() as connection:
            row = connection.execute(query).mappings().first()
        if row:
            value = row["gauge_height_m"] if row["gauge_height_m"] is not None else row["water_level_m"]
            result["river"] = {
                "timestamp": row["ts"],
                "level_m": float(value) if value is not None else None,
            }
    except Exception:
        pass

    return result