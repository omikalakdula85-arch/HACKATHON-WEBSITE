from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

try:
    from .clock import utc_now
    from .settings import MODEL_PATH
except ImportError:
    from clock import utc_now
    from settings import MODEL_PATH


MODEL_VERSION = "synthetic-rf-v1"


def train_and_save_model(path: Path = MODEL_PATH) -> None:
    rng = np.random.default_rng(20261117)
    sample_count = 2400
    day_of_week = rng.integers(0, 7, sample_count)
    area_density = rng.uniform(0.1, 1.0, sample_count)
    rainfall_mm = rng.gamma(shape=1.6, scale=8.0, size=sample_count).clip(0, 80)
    days_since_pickup = rng.integers(0, 15, sample_count)
    weekend_factor = np.isin(day_of_week, (5, 6)).astype(float)
    target_fill = (
        5
        + area_density * 38
        + days_since_pickup * 3.9
        + rainfall_mm * 0.2
        + weekend_factor * area_density * 10
        + rng.normal(0, 5, sample_count)
    ).clip(0, 100)
    features = np.column_stack((day_of_week, area_density, rainfall_mm, days_since_pickup))
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
    model.fit(features, target_fill)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "version": MODEL_VERSION,
        "trainedAt": utc_now().isoformat(),
        "featureNames": ["dayOfWeek", "areaDensity", "rainfallMm", "daysSincePickup"],
    }, path)


def ensure_model(path: Path = MODEL_PATH) -> None:
    if not path.is_file():
        train_and_save_model(path)


@lru_cache(maxsize=2)
def _load_model(path: str) -> dict[str, Any]:
    return joblib.load(path)


def predict_fill_level(
    *,
    area_density: float,
    days_since_pickup: int,
    rainfall_mm: float = 0,
    prediction_date: date | None = None,
    bin_capacity_kg: float = 120,
) -> dict[str, Any]:
    ensure_model(MODEL_PATH)
    bundle = _load_model(str(MODEL_PATH))
    model = bundle["model"]
    target_date = prediction_date or date.today()
    features = np.array([[
        target_date.weekday(),
        float(area_density),
        float(rainfall_mm),
        int(days_since_pickup),
    ]])
    tree_values = np.array([tree.predict(features)[0] for tree in model.estimators_])
    fill_percent = float(np.clip(tree_values.mean(), 0, 100))
    deviation = float(tree_values.std())
    return {
        "fillLevelPercent": round(fill_percent, 1),
        "estimatedWasteKg": round(float(bin_capacity_kg) * fill_percent / 100, 1),
        "confidenceRange": [
            round(float(np.clip(fill_percent - 1.96 * deviation, 0, 100)), 1),
            round(float(np.clip(fill_percent + 1.96 * deviation, 0, 100)), 1),
        ],
        "modelVersion": bundle["version"],
    }
