"""Leakage-aware baseline ML training/evaluation for project KPI next-snapshot data.

Models are fitted in memory only. The final chronological observations are held
out; this is a forecasting benchmark, not proof of production generalization.
"""
from __future__ import annotations

import math
from typing import Any

FEATURES = (
    "feature_SPI", "feature_CPI", "feature_risk_score",
    "feature_delayed_activity_count", "feature_overdue_action_count",
    "gap_days",
)
TARGETS = (
    "SPI", "CPI", "risk_score",
    "delayed_activity_count", "overdue_action_count",
)


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def train_historical_kpi_models(
    dataset_rows: list[dict[str, Any]],
    *,
    test_fraction: float = 0.2,
    minimum_training_rows: int = 8,
    random_state: int = 42,
) -> dict[str, Any]:
    """Fit one RandomForestRegressor per KPI using a chronological holdout.

    Input rows must come from the next-snapshot dataset builder. No project ID,
    future target or target-date field is used as a feature.
    """
    if not isinstance(dataset_rows, list) or any(not isinstance(row, dict) for row in dataset_rows):
        raise TypeError("dataset_rows must be a list of dictionaries")
    if isinstance(test_fraction, bool) or not isinstance(test_fraction, (int, float)) or not 0.1 <= test_fraction <= 0.4:
        raise ValueError("test_fraction must be between 0.1 and 0.4")
    if isinstance(minimum_training_rows, bool) or not isinstance(minimum_training_rows, int) or minimum_training_rows < 5:
        raise ValueError("minimum_training_rows must be an integer of at least 5")
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise ValueError("random_state must be an integer")

    if not dataset_rows:
        return {"status": "INSUFFICIENT_HISTORY", "models": {}, "metrics": [],
                "limitations": ["No next-snapshot rows are available."]}

    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.pipeline import make_pipeline
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    except ImportError as exc:
        raise RuntimeError("Install scikit-learn to train historical KPI models.") from exc

    dated_rows = []
    for index, row in enumerate(dataset_rows, 1):
        target_date = str(row.get("target_date", ""))[:10]
        if len(target_date) != 10:
            raise ValueError(f"Dataset row {index}: target_date must use YYYY-MM-DD")
        dated_rows.append((target_date, row))
    dated_rows.sort(key=lambda item: item[0])

    models: dict[str, Any] = {}
    metrics: list[dict[str, Any]] = []
    model_feature_columns: dict[str, list[str]] = {}
    for target in TARGETS:
        usable = []
        for target_date, row in dated_rows:
            y = _finite(row.get(f"target_{target}"))
            if y is None:
                continue
            x = [_finite(row.get(feature)) for feature in FEATURES]
            usable.append((target_date, x, y, _finite(row.get(f"feature_{target}"))))
        test_count = max(2, math.ceil(len(usable) * float(test_fraction)))
        train_count = len(usable) - test_count
        if train_count < minimum_training_rows or test_count < 2:
            metrics.append({
                "target": target, "status": "INSUFFICIENT_HISTORY",
                "usable_rows": len(usable), "training_rows": max(0, train_count),
                "test_rows": min(test_count, len(usable)),
            })
            continue

        train_rows, test_rows = usable[:train_count], usable[train_count:]
        # Drop columns that are entirely missing in the training window.
        # Determine this from training rows only to avoid holdout leakage.
        active_feature_indices = [
            index for index in range(len(FEATURES))
            if any(row[1][index] is not None for row in train_rows)
        ]
        if not active_feature_indices:
            metrics.append({
                "target": target, "status": "INSUFFICIENT_FEATURES",
                "usable_rows": len(usable), "training_rows": train_count,
                "test_rows": test_count,
            })
            continue
        active_feature_names = [FEATURES[index] for index in active_feature_indices]
        x_train = [[row[1][index] for index in active_feature_indices] for row in train_rows]
        y_train = [row[2] for row in train_rows]
        x_test = [[row[1][index] for index in active_feature_indices] for row in test_rows]
        y_test = [row[2] for row in test_rows]

        model = make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(
                n_estimators=100, min_samples_leaf=2,
                random_state=random_state, n_jobs=1,
            ),
        )
        model.fit(x_train, y_train)
        predictions = [float(value) for value in model.predict(x_test)]
        mae = float(mean_absolute_error(y_test, predictions))
        rmse = float(math.sqrt(mean_squared_error(y_test, predictions)))
        baseline_pairs = [(row[3], row[2]) for row in test_rows if row[3] is not None]
        baseline_mae = (
            float(mean_absolute_error(
                [pair[1] for pair in baseline_pairs],
                [pair[0] for pair in baseline_pairs],
            )) if baseline_pairs else None
        )
        metrics.append({
            "target": target, "status": "EVALUATED",
            "usable_rows": len(usable), "training_rows": train_count,
            "test_rows": test_count,
            "test_start_date": test_rows[0][0],
            "test_end_date": test_rows[-1][0],
            "mae": round(mae, 6), "rmse": round(rmse, 6),
            "persistence_baseline_mae": round(baseline_mae, 6) if baseline_mae is not None else None,
            "beats_persistence_baseline": (mae < baseline_mae) if baseline_mae is not None else None,
        })
        models[target] = model
        model_feature_columns[target] = active_feature_names

    return {
        "status": "EVALUATED" if models else "INSUFFICIENT_HISTORY",
        "model_family": "RandomForestRegressor with median imputation",
        "split_method": "Chronological holdout by target_date; latest observations are test data.",
        "feature_columns": list(FEATURES),
        "model_feature_columns": model_feature_columns,
        "target_columns": [f"target_{target}" for target in TARGETS],
        "metrics": metrics,
        "models": models,
        "limitations": [
            "Models are in-memory only; no model artifact is persisted or deployed.",
            "Small or non-representative project histories can produce unstable metrics.",
            "The chronological holdout is not a substitute for external project validation.",
            "Adjacent observations can be correlated; interpret metrics cautiously.",
            "Compare against the persistence baseline; a model that does not beat it should not be promoted.",
            "No probability of project failure or causal effect is estimated.",
        ],
    }
