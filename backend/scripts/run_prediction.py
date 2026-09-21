import os
import sys
import joblib
import numpy as np
import pandas as pd

from datetime import datetime, timezone

# ============================================================
# ADD PROJECT ROOT TO PYTHON PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# ============================================================
# PATH CONFIGURATION
# ============================================================

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "chamoli_flood_model.joblib"
)

GRID_FILE = os.path.join(
    DATA_DIR,
    "chamoli_static_ml_dataset.csv"
)


RAINFALL_FILE = os.path.join(
    DATA_DIR,
    "RAINFALL Dataset from 2000-2026.csv"
)

SOIL_FILE = os.path.join(
    DATA_DIR,
    "soil moisture datset from 2000-2026.csv"
)

WATER_FILE = os.path.join(
    DATA_DIR,
    "Alaknanda_Joshimath_water_level_hourly_updated.csv"
)


# ============================================================
# DATABASE
# ============================================================

from sqlalchemy import create_engine, text

try:
    from app.config import settings
    import os
    from dotenv import load_dotenv

    # Force load the .env file from the backend folder
    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

    # Fallback: check settings first, then check the loaded environment variables
    DATABASE_URL = getattr(settings, "DATABASE_URL", os.getenv("DATABASE_URL"))

except Exception:

    DATABASE_URL = os.getenv(
        "DATABASE_URL"
    )

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Check backend/.env"
        )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    print("\nLoading trained model...")

    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_FILE}\n\n"
            "Run train_model.py first."
        )

    bundle = joblib.load(
        MODEL_FILE
    )

    if not isinstance(bundle, dict):
        raise RuntimeError(
            "The saved model is not the expected model bundle."
        )

    required_keys = [
        "model",
        "features",
        "threshold",
        "horizon_hours",
        "model_version"
    ]

    missing = [
        key
        for key in required_keys
        if key not in bundle
    ]

    if missing:
        raise RuntimeError(
            "Model bundle is missing: "
            + ", ".join(missing)
        )

    model = bundle["model"]
    features = bundle["features"]
    threshold = float(
        bundle["threshold"]
    )
    horizon_hours = int(
        bundle["horizon_hours"]
    )
    model_version = bundle[
        "model_version"
    ]

    print(
        f"Model version : {model_version}"
    )

    print(
        f"Horizon       : {horizon_hours} hours"
    )

    print(
        f"Threshold     : {threshold:.2f}"
    )

    print(
        f"Features      : {len(features)}"
    )

    return (
        model,
        features,
        threshold,
        horizon_hours,
        model_version
    )


# ============================================================
# LOAD RAINFALL
# ============================================================

def load_rainfall():

    print(
        "\nLoading latest rainfall data..."
    )

    df = pd.read_csv(
        RAINFALL_FILE,
        skiprows=3,
        low_memory=False
    )

    time_col = df.columns[0]
    rain_col = df.columns[1]

    df = df.rename(
        columns={
            time_col: "timestamp",
            rain_col: "rainfall_mm"
        }
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df["rainfall_mm"] = pd.to_numeric(
        df["rainfall_mm"],
        errors="coerce"
    ).fillna(0)

    df = df.dropna(
        subset=["timestamp"]
    )

    df = (
        df.sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    df = (
        df.set_index("timestamp")
        [["rainfall_mm"]]
        .resample("1h")
        .sum()
        .fillna(0)
        .reset_index()
    )

    return df


# ============================================================
# LOAD SOIL MOISTURE
# ============================================================

def load_soil():

    print(
        "Loading latest soil moisture data..."
    )

    df = pd.read_csv(
        SOIL_FILE,
        skiprows=3,
        low_memory=False
    )

    time_col = df.columns[0]

    df = df.rename(
        columns={
            time_col: "timestamp"
        }
    )

    soil_rename = {
        col: f"soil_{i}"
        for i, col in enumerate(
            df.columns[1:]
        )
    }

    df = df.rename(
        columns=soil_rename
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp"]
    )

    soil_cols = [
        c
        for c in df.columns
        if c.startswith("soil_")
    ]

    for col in soil_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = (
        df.sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    df = (
        df.set_index("timestamp")
        [soil_cols]
        .resample("1h")
        .mean()
        .interpolate(method="time")
        .ffill()
        .bfill()
        .reset_index()
    )

    return df


# ============================================================
# LOAD RIVER LEVEL
# ============================================================

def load_water():

    print(
        "Loading latest river level data..."
    )

    df = pd.read_csv(
        WATER_FILE,
        low_memory=False
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        dayfirst=True,
        errors="coerce"
    )

    df["water_level_m"] = pd.to_numeric(
        df["measured_water_level_m"],
        errors="coerce"
    )

    # The training code uses gauge height when available.
    if (
        "gauge_height_above_zero_m"
        in df.columns
    ):

        df["gauge_height_m"] = pd.to_numeric(
            df[
                "gauge_height_above_zero_m"
            ],
            errors="coerce"
        )

        df["water_level_m"] = (
            df["gauge_height_m"]
            .fillna(
                df["water_level_m"]
            )
        )

    df = df.dropna(
        subset=[
            "timestamp",
            "water_level_m"
        ]
    )

    df = (
        df.sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    df = (
        df.set_index("timestamp")
        [["water_level_m"]]
        .resample("1h")
        .mean()
        .interpolate(method="time")
        .ffill()
        .bfill()
        .reset_index()
    )

    return df


# ============================================================
# BUILD CURRENT FEATURES
# ============================================================

def build_current_features():

    rainfall = load_rainfall()

    soil = load_soil()

    water = load_water()

    print(
        "\nCombining environmental data..."
    )

    # --------------------------------------------------------
    # Start with rainfall hourly timeline
    # --------------------------------------------------------

    df = rainfall.copy()

    # --------------------------------------------------------
    # Merge soil
    # --------------------------------------------------------

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        soil.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(
            hours=3
        )
    )

    # --------------------------------------------------------
    # Merge river
    # --------------------------------------------------------

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        water.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(
            hours=3
        )
    )

    # --------------------------------------------------------
    # Soil columns
    # --------------------------------------------------------

    soil_cols = [
        c
        for c in df.columns
        if c.startswith("soil_")
    ]

    for col in soil_cols:

        df[col] = (
            pd.to_numeric(
                df[col],
                errors="coerce"
            )
            .interpolate()
            .ffill()
            .bfill()
        )

    # --------------------------------------------------------
    # River
    # --------------------------------------------------------

    df["water_level_m"] = (
        pd.to_numeric(
            df["water_level_m"],
            errors="coerce"
        )
        .interpolate()
        .ffill()
        .bfill()
    )

    # --------------------------------------------------------
    # Rainfall features
    #
    # EXACTLY matching train_model.py
    # --------------------------------------------------------

    df["rain_1h"] = (
        df["rainfall_mm"]
    )

    df["rain_3h"] = (
        df["rainfall_mm"]
        .rolling(
            3,
            min_periods=1
        )
        .sum()
    )

    df["rain_6h"] = (
        df["rainfall_mm"]
        .rolling(
            6,
            min_periods=1
        )
        .sum()
    )

    df["rain_12h"] = (
        df["rainfall_mm"]
        .rolling(
            12,
            min_periods=1
        )
        .sum()
    )

    df["rain_24h"] = (
        df["rainfall_mm"]
        .rolling(
            24,
            min_periods=1
        )
        .sum()
    )

    df["rain_change_3h"] = (
        df["rain_1h"]
        .rolling(
            3,
            min_periods=1
        )
        .mean()
    )

    # --------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------

    if soil_cols:

        df["soil_mean"] = (
            df[soil_cols]
            .mean(axis=1)
        )

    else:

        df["soil_mean"] = 0.0

    # --------------------------------------------------------
    # River changes
    # --------------------------------------------------------

    df["river_change_3h"] = (
        df["water_level_m"]
        -
        df["water_level_m"].shift(3)
    )

    df["river_change_6h"] = (
        df["water_level_m"]
        -
        df["water_level_m"].shift(6)
    )

    df["river_change_12h"] = (
        df["water_level_m"]
        -
        df["water_level_m"].shift(12)
    )

    df[
        [
            "river_change_3h",
            "river_change_6h",
            "river_change_12h"
        ]
    ] = (
        df[
            [
                "river_change_3h",
                "river_change_6h",
                "river_change_12h"
            ]
        ]
        .fillna(0)
    )

    # --------------------------------------------------------
    # Time features
    # --------------------------------------------------------

    df["month"] = (
        df["timestamp"].dt.month
    )

    df["hour"] = (
        df["timestamp"].dt.hour
    )

    df["day_of_year"] = (
        df["timestamp"].dt.dayofyear
    )

    # --------------------------------------------------------
    # Cyclic time features
    # --------------------------------------------------------

    df["month_sin"] = np.sin(
        2 * np.pi * df["month"] / 12
    )

    df["month_cos"] = np.cos(
        2 * np.pi * df["month"] / 12
    )

    df["hour_sin"] = np.sin(
        2 * np.pi * df["hour"] / 24
    )

    df["hour_cos"] = np.cos(
        2 * np.pi * df["hour"] / 24
    )

    # --------------------------------------------------------
    # Remove invalid rows
    # --------------------------------------------------------

    df = (
        df.replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
        .reset_index(drop=True)
    )

    if len(df) == 0:

        raise RuntimeError(
            "No valid environmental feature rows were created."
        )

    # --------------------------------------------------------
    # Latest available row
    # --------------------------------------------------------

    latest = df.iloc[-1].copy()

    latest_timestamp = (
        latest["timestamp"]
    )

    print(
        "\nLatest environmental observation:"
    )

    print(
        f"Timestamp       : "
        f"{latest_timestamp}"
    )

    print(
        f"Rainfall 1h     : "
        f"{latest['rain_1h']:.3f} mm"
    )

    print(
        f"Rainfall 3h     : "
        f"{latest['rain_3h']:.3f} mm"
    )

    print(
        f"Rainfall 6h     : "
        f"{latest['rain_6h']:.3f} mm"
    )

    print(
        f"Rainfall 24h    : "
        f"{latest['rain_24h']:.3f} mm"
    )

    print(
        f"Soil moisture   : "
        f"{latest['soil_mean']:.4f}"
    )

    print(
        f"River level     : "
        f"{latest['water_level_m']:.3f} m"
    )

    print(
        f"River change 6h : "
        f"{latest['river_change_6h']:.3f} m"
    )

    return latest


# ============================================================
# LOAD TERRAIN GRID
# ============================================================

def load_terrain_grid():

    print(
        "\nLoading Chamoli terrain grid..."
    )

    if not os.path.exists(
        GRID_FILE
    ):

        raise FileNotFoundError(
            f"Terrain grid not found:\n"
            f"{GRID_FILE}"
        )

    grid = pd.read_csv(
        GRID_FILE
    )

    required_columns = [
        "grid_id",
        "latitude",
        "longitude",
        "elevation_m",
        "slope_deg",
        "distance_to_river_m"
    ]

    missing = [
        col
        for col in required_columns
        if col not in grid.columns
    ]

    if missing:

        raise ValueError(
            "Terrain grid is missing columns: "
            + ", ".join(missing)
        )

    grid = grid[
        required_columns
    ].copy()

    for col in required_columns:

        if col != "grid_id":

            grid[col] = pd.to_numeric(
                grid[col],
                errors="coerce"
            )

    grid = grid.dropna()

    print(
        f"Terrain grid cells: "
        f"{len(grid):,}"
    )

    return grid


# ============================================================
# TERRAIN SUSCEPTIBILITY
# ============================================================

def calculate_susceptibility(grid):

    """
    Calculate a transparent spatial susceptibility score.

    IMPORTANT:
    This is NOT a learned Random Forest feature.

    It is a secondary spatial modifier used to create
    location-specific risk from:
        - elevation
        - slope
        - distance to river
    """

    result = grid.copy()

    # --------------------------------------------------------
    # Normalize helper
    # --------------------------------------------------------

    def normalize(series):

        minimum = series.min()
        maximum = series.max()

        if maximum == minimum:

            return pd.Series(
                0.5,
                index=series.index
            )

        return (
            (series - minimum)
            / (maximum - minimum)
        )

    # --------------------------------------------------------
    # Low elevation
    # --------------------------------------------------------

    elevation_norm = normalize(
        result["elevation_m"]
    )

    low_elevation_risk = (
        1.0 - elevation_norm
    )

    # --------------------------------------------------------
    # Slope
    #
    # Extremely steep terrain is not automatically treated
    # as a flood trigger. We use a bounded susceptibility
    # transform rather than assuming "higher slope = flood".
    # --------------------------------------------------------

    slope_norm = normalize(
        result["slope_deg"]
    )

    # Moderate/low slope areas are given more flood
    # accumulation susceptibility.
    slope_flood_component = (
        1.0 - slope_norm
    )

    # --------------------------------------------------------
    # Distance from river
    # --------------------------------------------------------

    distance_norm = normalize(
        result["distance_to_river_m"]
    )

    river_proximity = (
        1.0 - distance_norm
    )

    # --------------------------------------------------------
    # Weighted spatial susceptibility
    # --------------------------------------------------------

    result["susceptibility"] = (
        0.20 * low_elevation_risk
        +
        0.20 * slope_flood_component
        +
        0.60 * river_proximity
    )

    result["susceptibility"] = (
        result["susceptibility"]
        .clip(0, 1)
    )

    return result


# ============================================================
# ALERT LEVEL
# ============================================================

def get_alert_level(
    probability,
    threshold
):
    """
    Convert final probability into dashboard alert level.

    The trained model threshold is treated as the RED
    decision threshold.

    Other levels are fractions of that threshold so that
    the dashboard still provides graded information.
    """

    # Prevent zero threshold
    threshold = max(
        float(threshold),
        0.01
    )

    if probability >= threshold:

        return "RED"

    elif probability >= threshold * 0.75:

        return "ORANGE"

    elif probability >= threshold * 0.50:

        return "YELLOW"

    else:

        return "GREEN"


# ============================================================
# EXPLANATION
# ============================================================

def create_explanation(
    latest,
    probability,
    susceptibility,
    alert_level
):

    reasons = []

    if latest["rain_6h"] >= 30:
        reasons.append(
            "high recent rainfall"
        )

    if latest["rain_24h"] >= 50:
        reasons.append(
            "high 24-hour rainfall accumulation"
        )

    if latest["soil_mean"] >= 0.70:
        reasons.append(
            "high soil moisture"
        )

    if latest["river_change_6h"] > 0:
        reasons.append(
            "rising river level"
        )

    if susceptibility >= 0.70:
        reasons.append(
            "high spatial susceptibility"
        )

    if not reasons:

        reasons.append(
            "no dominant extreme environmental trigger detected"
        )

    return (
        f"{alert_level} risk. "
        f"Temporal model probability "
        f"{probability:.1%}. "
        f"Spatial susceptibility "
        f"{susceptibility:.1%}. "
        f"Factors: "
        + ", ".join(reasons)
        + "."
    )


# ============================================================
# SAVE PREDICTIONS TO POSTGRESQL
# ============================================================

def save_predictions(
    predictions,
    generated_at
):

    print(
        "\nSaving predictions to PostgreSQL..."
    )

    # --------------------------------------------------------
    # Clear previous prediction snapshot.
    #
    # We keep the database table as the latest dashboard
    # prediction snapshot.
    # --------------------------------------------------------

    with engine.begin() as connection:

        connection.execute(
            text(
                "DELETE FROM flood_predictions"
            )
        )

        insert_query = text(
            """
            INSERT INTO flood_predictions
            (
                generated_at,
                grid_id,
                horizon_hours,
                flood_probability,
                risk_score,
                alert_level,
                explanation,
                model_version
            )
            VALUES
            (
                :generated_at,
                :grid_id,
                :horizon_hours,
                :flood_probability,
                :risk_score,
                :alert_level,
                :explanation,
                :model_version
            )
            """
        )

        records = (
            predictions
            .to_dict(
                orient="records"
            )
        )

        connection.execute(
            insert_query,
            records
        )

    print(
        f"Saved {len(predictions):,} predictions."
    )


# ============================================================
# MAIN PREDICTION PIPELINE
# ============================================================

def run_prediction():

    print("=" * 70)
    print(
        "CHAMOLI FLASH-FLOOD PREDICTION"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    (
        model,
        feature_columns,
        threshold,
        horizon_hours,
        model_version
    ) = load_model()

    # --------------------------------------------------------
    # Build latest environmental features
    # --------------------------------------------------------

    latest = build_current_features()

    # --------------------------------------------------------
    # Prepare RF input
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in latest.index
    ]

    if missing_features:

        raise RuntimeError(
            "Current prediction features do not match "
            "the trained model.\nMissing:\n"
            + "\n".join(
                missing_features
            )
        )

    X_current = pd.DataFrame(
        [
            [
                latest[feature]
                for feature in feature_columns
            ]
        ],
        columns=feature_columns
    )

    # --------------------------------------------------------
    # Temporal probability
    # --------------------------------------------------------

    temporal_probability = float(
        model.predict_proba(
            X_current
        )[0, 1]
    )

    print("\n" + "=" * 70)
    print(
        "TEMPORAL MODEL RESULT"
    )
    print("=" * 70)

    print(
        f"Temporal flood probability: "
        f"{temporal_probability:.4f}"
    )

    print(
        f"Training threshold: "
        f"{threshold:.4f}"
    )

    # --------------------------------------------------------
    # Load terrain grid
    # --------------------------------------------------------

    grid = load_terrain_grid()

    grid = calculate_susceptibility(
        grid
    )

    # --------------------------------------------------------
    # Late multimodal fusion
    #
    # IMPORTANT:
    # RF was trained only on temporal/environmental features.
    # Terrain is therefore introduced here as a transparent
    # spatial modifier.
    # --------------------------------------------------------

    grid["temporal_probability"] = (
        temporal_probability
    )

    grid["flood_probability"] = (
        0.75
        * grid["temporal_probability"]
        +
        0.25
        * grid["susceptibility"]
    )

    grid["flood_probability"] = (
        grid["flood_probability"]
        .clip(0, 1)
    )

    # --------------------------------------------------------
    # Risk score
    # --------------------------------------------------------

    grid["risk_score"] = (
        grid["flood_probability"]
        * 100.0
    )

    # --------------------------------------------------------
    # Alert level
    # --------------------------------------------------------

    grid["alert_level"] = [
        get_alert_level(
            probability,
            threshold
        )
        for probability in
        grid["flood_probability"]
    ]

    # --------------------------------------------------------
    # Explanations
    # --------------------------------------------------------

    grid["explanation"] = [
        create_explanation(
            latest,
            probability,
            susceptibility,
            alert
        )
        for probability,
        susceptibility,
        alert
        in zip(
            grid["flood_probability"],
            grid["susceptibility"],
            grid["alert_level"]
        )
    ]

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    generated_at = datetime.now(
        timezone.utc
    )

    grid["generated_at"] = (
        generated_at
    )

    grid["horizon_hours"] = (
        horizon_hours
    )

    grid["model_version"] = (
        model_version
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_predictions(
        grid[
            [
                "generated_at",
                "grid_id",
                "horizon_hours",
                "flood_probability",
                "risk_score",
                "alert_level",
                "explanation",
                "model_version"
            ]
        ],
        generated_at
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print(
        "PREDICTION SUMMARY"
    )
    print("=" * 70)

    counts = (
        grid["alert_level"]
        .value_counts()
    )

    print(
        f"RED cells    : "
        f"{counts.get('RED', 0):,}"
    )

    print(
        f"ORANGE cells : "
        f"{counts.get('ORANGE', 0):,}"
    )

    print(
        f"YELLOW cells : "
        f"{counts.get('YELLOW', 0):,}"
    )

    print(
        f"GREEN cells  : "
        f"{counts.get('GREEN', 0):,}"
    )

    print(
        f"\nAverage risk : "
        f"{grid['risk_score'].mean():.2f}"
    )

    print(
        f"Maximum risk : "
        f"{grid['risk_score'].max():.2f}"
    )

    print(
        f"\nTemporal probability : "
        f"{temporal_probability:.2%}"
    )

    print(
        f"Prediction horizon   : "
        f"{horizon_hours} hours"
    )

    print(
        f"Model version        : "
        f"{model_version}"
    )

    print("\nPrediction completed successfully.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        run_prediction()

    except Exception as error:

        print("\n" + "=" * 70)
        print("PREDICTION FAILED")
        print("=" * 70)

        print(
            f"{type(error).__name__}: {error}"
        )

        raise
