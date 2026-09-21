import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(MODEL_DIR, exist_ok=True)

RAINFALL_FILE = os.path.join(DATA_DIR, "RAINFALL Dataset from 2000-2026.csv")
SOIL_FILE = os.path.join(DATA_DIR, "soil moisture datset from 2000-2026.csv")
WATER_FILE = os.path.join(
    DATA_DIR, "Alaknanda_Joshimath_water_level_hourly_updated.csv"
)
EVENT_FILE = os.path.join(DATA_DIR, "chamoli_flood_events_2000_2026.csv")

MODEL_FILE = os.path.join(MODEL_DIR, "chamoli_flood_model.joblib")
METRICS_FILE = os.path.join(MODEL_DIR, "training_metrics.json")


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def load_rainfall():
    """Load rainfall dataset (skipping header metadata rows)."""
    print("\nLoading rainfall data...")

    # Skip 3 header metadata rows
    df = pd.read_csv(RAINFALL_FILE, skiprows=3, low_memory=False)

    time_col = df.columns[0]
    rain_col = df.columns[1]

    df = df.rename(columns={time_col: "timestamp", rain_col: "rainfall_mm"})

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["rainfall_mm"] = pd.to_numeric(
        df["rainfall_mm"], errors="coerce"
    ).fillna(0)

    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")

    # Convert to hourly frequency selecting numeric column only
    df = (
        df.set_index("timestamp")[["rainfall_mm"]]
        .resample("1h")
        .sum()
        .fillna(0)
        .reset_index()
    )

    print(f"Rainfall rows after preprocessing: {len(df):,}")
    return df


def load_soil():
    """Load soil moisture dataset (skipping header metadata rows)."""
    print("\nLoading soil moisture data...")

    # Skip 3 header metadata rows
    df = pd.read_csv(SOIL_FILE, skiprows=3, low_memory=False)

    time_col = df.columns[0]
    df = df.rename(columns={time_col: "timestamp"})

    # Rename soil depth columns dynamically
    soil_rename = {
        col: f"soil_{i}" for i, col in enumerate(df.columns[1:])
    }
    df = df.rename(columns=soil_rename)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    soil_cols = [c for c in df.columns if c.startswith("soil_")]
    for col in soil_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("timestamp").drop_duplicates("timestamp")

    # Resample to hourly mean selecting numeric soil columns only
    df = (
        df.set_index("timestamp")[soil_cols]
        .resample("1h")
        .mean()
        .interpolate(method="time")
        .ffill()
        .bfill()
        .reset_index()
    )

    print(f"Soil moisture rows after preprocessing: {len(df):,}")
    return df


def load_water():
    """Load Alaknanda/Joshimath water-level observations."""
    print("\nLoading river water-level data...")

    df = pd.read_csv(WATER_FILE)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], dayfirst=True, errors="coerce"
    )
    df["water_level_m"] = pd.to_numeric(
        df["measured_water_level_m"], errors="coerce"
    )

    if "gauge_height_above_zero_m" in df.columns:
        df["gauge_height_m"] = pd.to_numeric(
            df["gauge_height_above_zero_m"], errors="coerce"
        )
        df["water_level_m"] = df["gauge_height_m"].fillna(df["water_level_m"])

    df = df.dropna(subset=["timestamp", "water_level_m"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")

    # Resample selecting numeric water level column only
    df = (
        df.set_index("timestamp")[["water_level_m"]]
        .resample("1h")
        .mean()
        .interpolate(method="time")
        .ffill()
        .bfill()
        .reset_index()
    )

    print(f"River rows after preprocessing: {len(df):,}")
    return df


def load_events():
    """Load verified historical Chamoli flood events."""
    print("\nLoading historical flood events...")

    df = pd.read_csv(EVENT_FILE)

    # Use actual column names from dataset: event_date and event_end_date
    df["start_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["event_end_date"], errors="coerce")

    # If end_date is missing, default to 24 hours after start_date
    df["end_date"] = df["end_date"].fillna(
        df["start_date"] + pd.Timedelta(hours=24)
    )

    df = df.dropna(subset=["start_date", "end_date"])

    print(f"Historical flood events: {len(df)}")
    return df


# ============================================================
# FLOOD LABEL CREATION
# ============================================================


def create_future_flood_target(timestamps, events_df, horizon_hours=24):
    """
    Create a future-looking flood target.
    target = 1 when a verified historical flood event occurs within next horizon_hours.
    """
    target = np.zeros(len(timestamps), dtype=np.int8)
    timestamp_values = pd.Series(pd.to_datetime(timestamps))

    for _, event in events_df.iterrows():
        event_start = event["start_date"]
        event_end = event["end_date"]

        prediction_start = event_start - pd.Timedelta(hours=horizon_hours)
        prediction_end = event_end

        mask = (timestamp_values >= prediction_start) & (
            timestamp_values <= prediction_end
        )

        target[mask.values] = 1

    return target


# ============================================================
# FEATURE ENGINEERING
# ============================================================


def build_dataset():
    rainfall = load_rainfall()
    soil = load_soil()
    river = load_water()
    events = load_events()

    print("\nCombining datasets...")

    df = rainfall.copy()

    # Merge soil moisture
    df = pd.merge_asof(
        df.sort_values("timestamp"),
        soil.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(hours=3),
    )

    # Merge river level
    df = pd.merge_asof(
        df.sort_values("timestamp"),
        river.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(hours=3),
    )

    # Fill missing environmental values
    soil_cols = [c for c in df.columns if c.startswith("soil_")]
    for col in soil_cols:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce").interpolate().ffill().bfill()
        )

    df["water_level_m"] = (
        pd.to_numeric(df["water_level_m"], errors="coerce")
        .interpolate()
        .ffill()
        .bfill()
    )

    # Rainfall rolling windows
    df["rain_1h"] = df["rainfall_mm"]
    df["rain_3h"] = df["rainfall_mm"].rolling(3, min_periods=1).sum()
    df["rain_6h"] = df["rainfall_mm"].rolling(6, min_periods=1).sum()
    df["rain_12h"] = df["rainfall_mm"].rolling(12, min_periods=1).sum()
    df["rain_24h"] = df["rainfall_mm"].rolling(24, min_periods=1).sum()

    df["rain_change_3h"] = df["rain_1h"].rolling(3, min_periods=1).mean()

    # Soil moisture aggregate
    df["soil_mean"] = df[soil_cols].mean(axis=1) if soil_cols else 0

    # River change
    df["river_change_3h"] = df["water_level_m"] - df["water_level_m"].shift(3)
    df["river_change_6h"] = df["water_level_m"] - df["water_level_m"].shift(6)
    df["river_change_12h"] = df["water_level_m"] - df["water_level_m"].shift(
        12
    )

    df[["river_change_3h", "river_change_6h", "river_change_12h"]] = df[
        ["river_change_3h", "river_change_6h", "river_change_12h"]
    ].fillna(0)

    # Time features
    df["month"] = df["timestamp"].dt.month
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_year"] = df["timestamp"].dt.dayofyear

    # Cyclic representation
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Create 24-hour future flood target
    df["is_flood"] = create_future_flood_target(
        df["timestamp"], events, horizon_hours=24
    )

    df = df.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    return df


# ============================================================
# THRESHOLD EVALUATION
# ============================================================


def evaluate_thresholds(y_true, probabilities):
    thresholds = [
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
        0.35,
        0.40,
        0.45,
        0.50,
        0.55,
        0.60,
        0.65,
        0.70,
        0.75,
    ]

    rows = []
    total_negative = int(np.sum(y_true == 0))

    for threshold in thresholds:
        predictions = (probabilities >= threshold).astype(int)

        tn, fp, fn, tp = confusion_matrix(
            y_true, predictions, labels=[0, 1]
        ).ravel()

        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        f1 = f1_score(y_true, predictions, zero_division=0)

        false_alarm_rate = fp / total_negative if total_negative > 0 else 0

        rows.append({
            "threshold": threshold,
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
        })

    return pd.DataFrame(rows)


# ============================================================
# MODEL TRAINING
# ============================================================


def train_model():
    print("=" * 70)
    print("CHAMOLI FLASH-FLOOD MODEL TRAINING")
    print("=" * 70)

    df = build_dataset()

    print("\nFinal dataset:")
    print(f"Rows: {len(df):,}")
    print(f"Positive flood rows: {int(df['is_flood'].sum()):,}")
    print(f"Negative rows: {int((df['is_flood'] == 0).sum()):,}")

    positive_ratio = df["is_flood"].mean()
    print(f"Positive ratio: {positive_ratio:.4%}")

    feature_columns = [
        "rain_1h",
        "rain_3h",
        "rain_6h",
        "rain_12h",
        "rain_24h",
        "rain_change_3h",
        "soil_mean",
        "water_level_m",
        "river_change_3h",
        "river_change_6h",
        "river_change_12h",
        "month",
        "hour",
        "day_of_year",
        "month_sin",
        "month_cos",
        "hour_sin",
        "hour_cos",
    ]

    X = df[feature_columns].copy()
    y = df["is_flood"].astype(int)

    # Chronological Train/Test Split
    split_index = int(len(df) * 0.80)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    print("\nChronological split:")
    print(f"Training rows: {len(X_train):,}")
    print(f"Testing rows: {len(X_test):,}")
    print(f"Training positives: {int(y_train.sum()):,}")
    print(f"Testing positives: {int(y_test.sum()):,}")

    if y_train.sum() == 0:
        raise RuntimeError(
            "Training set contains no positive flood examples."
        )

    if y_test.sum() == 0:
        raise RuntimeError("Test set contains no positive flood examples.")

    print("\nTraining Random Forest...")

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=16,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]

    roc_auc = roc_auc_score(y_test, probabilities)
    pr_auc = average_precision_score(y_test, probabilities)

    print("\n" + "=" * 70)
    print("PROBABILITY-BASED PERFORMANCE")
    print("=" * 70)
    print(f"ROC-AUC : {roc_auc:.4f}")
    print(f"PR-AUC  : {pr_auc:.4f}")

    threshold_table = evaluate_thresholds(y_test, probabilities)

    print("\n" + "=" * 70)
    print("THRESHOLD ANALYSIS")
    print("=" * 70)
    print(threshold_table.to_string(index=False))

    recall_target = 0.50
    eligible = threshold_table[threshold_table["recall"] >= recall_target]

    if len(eligible) > 0:
        selected_row = eligible.sort_values(
            ["f1", "recall"], ascending=False
        ).iloc[0]
    else:
        selected_row = threshold_table.sort_values(
            ["f1", "recall"], ascending=False
        ).iloc[0]

    selected_threshold = float(selected_row["threshold"])

    print("\n" + "=" * 70)
    print("SELECTED EARLY-WARNING THRESHOLD")
    print("=" * 70)
    print(f"Threshold : {selected_threshold:.2f}")
    print(f"Precision : {selected_row['precision']:.4f}")
    print(f"Recall    : {selected_row['recall']:.4f}")
    print(f"F1        : {selected_row['f1']:.4f}")
    print(f"False Alarm Rate : {selected_row['false_alarm_rate']:.4f}")

    final_predictions = (probabilities >= selected_threshold).astype(int)
    cm = confusion_matrix(y_test, final_predictions, labels=[0, 1])

    print("\n" + "=" * 70)
    print("CONFUSION MATRIX")
    print("=" * 70)
    print(cm)

    print("\nClassification Report:")
    print(
        classification_report(
            y_test, final_predictions, digits=4, zero_division=0
        )
    )

    importance = pd.DataFrame({
        "feature": feature_columns,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    print("\n" + "=" * 70)
    print("FEATURE IMPORTANCE")
    print("=" * 70)
    print(importance.to_string(index=False))

    model_bundle = {
        "model": model,
        "features": feature_columns,
        "threshold": selected_threshold,
        "horizon_hours": 24,
        "model_version": "chamoli-multimodal-flood-v2",
    }

    joblib.dump(model_bundle, MODEL_FILE)

    metrics = {
        "rows": int(len(df)),
        "positive_rows": int(y.sum()),
        "negative_rows": int((y == 0).sum()),
        "positive_ratio": float(positive_ratio),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_positive": int(y_train.sum()),
        "test_positive": int(y_test.sum()),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "selected_threshold": float(selected_threshold),
        "selected_precision": float(selected_row["precision"]),
        "selected_recall": float(selected_row["recall"]),
        "selected_f1": float(selected_row["f1"]),
        "false_alarm_rate": float(selected_row["false_alarm_rate"]),
        "confusion_matrix": cm.tolist(),
        "feature_importance": importance.to_dict(orient="records"),
        "threshold_table": threshold_table.to_dict(orient="records"),
    }

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 70)
    print("MODEL SAVED")
    print("=" * 70)
    print(f"Model: {MODEL_FILE}")
    print(f"Metrics: {METRICS_FILE}")
    print("\nTraining completed successfully.")


if __name__ == "__main__":
    train_model()