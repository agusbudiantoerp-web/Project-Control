"""Transparent trend-based early warning from dated project-control snapshots.

This is linear extrapolation for review, not a trained ML model or a causal
forecast. A minimum of three dated observations is required per metric.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

LOWER_IS_WORSE = {"SPI": 0.95, "CPI": 0.95}
HIGHER_IS_WORSE = {"risk_score": 75.0, "delayed_activity_count": 1.0, "overdue_action_count": 1.0}


def _day(value: Any, index: int) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError(f"Snapshot {index}: date must be YYYY-MM-DD") from None


def _value(value: Any, metric: str) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    if metric in {"SPI", "CPI"} and result < 0:
        raise ValueError(f"{metric} cannot be negative")
    if metric in {"risk_score", "delayed_activity_count", "overdue_action_count"} and result < 0:
        raise ValueError(f"{metric} cannot be negative")
    return result


def _regression(points: list[tuple[float, float]]) -> tuple[float, float]:
    x_mean = sum(x for x, _ in points) / len(points)
    y_mean = sum(y for _, y in points) / len(points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    if denominator == 0:
        raise ValueError("snapshot dates must be distinct")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    return slope, y_mean - slope * x_mean


def forecast_project_control_trends(
    snapshots: list[dict[str, Any]],
    *,
    horizon_days: int = 30,
    minimum_observations: int = 3,
) -> dict[str, Any]:
    """Extrapolate project KPI trends using dated snapshots.

    Each snapshot: {date, project_id, SPI?, CPI?, risk_score?,
    delayed_activity_count?, overdue_action_count?}. Missing metric values are
    skipped independently. Forecasts are not clamped to KPI bounds.
    """
    if not isinstance(snapshots, list) or any(not isinstance(row, dict) for row in snapshots):
        raise TypeError("snapshots must be a list of dictionaries")
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or not 1 <= horizon_days <= 365:
        raise ValueError("horizon_days must be an integer between 1 and 365")
    if isinstance(minimum_observations, bool) or not isinstance(minimum_observations, int) or minimum_observations < 3:
        raise ValueError("minimum_observations must be an integer of at least 3")

    groups: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(snapshots, 1):
        project_id = str(row.get("project_id", "")).strip()
        if not project_id:
            raise ValueError(f"Snapshot {index}: project_id is required")
        groups.setdefault(project_id, []).append({**row, "_date": _day(row.get("date"), index)})

    results = []
    for project_id, rows in sorted(groups.items()):
        rows.sort(key=lambda row: row["_date"])
        dates = [row["_date"] for row in rows]
        if len(set(dates)) != len(dates):
            raise ValueError(f"{project_id}: duplicate snapshot dates")
        origin = dates[0]
        metric_results = []
        for metric in (*LOWER_IS_WORSE, *HIGHER_IS_WORSE):
            points = []
            for row in rows:
                value = _value(row.get(metric), metric)
                if value is not None:
                    points.append(((row["_date"] - origin).days, value))
            if len(points) < minimum_observations:
                metric_results.append({
                    "metric": metric, "status": "INSUFFICIENT_HISTORY",
                    "observations": len(points), "forecast": None, "daily_slope": None,
                })
                continue
            slope, intercept = _regression(points)
            last_day = max(x for x, _ in points)
            forecast_day = last_day + horizon_days
            projected = slope * forecast_day + intercept
            latest = max(points, key=lambda item: item[0])[1]
            threshold = (LOWER_IS_WORSE | HIGHER_IS_WORSE)[metric]
            adverse_direction = slope < 0 if metric in LOWER_IS_WORSE else slope > 0
            currently_adverse = latest < threshold if metric in LOWER_IS_WORSE else latest >= threshold
            projected_adverse = projected < threshold if metric in LOWER_IS_WORSE else projected >= threshold
            if currently_adverse:
                status = "CURRENTLY_ADVERSE"
            elif adverse_direction and projected_adverse:
                status = "PROJECTED_THRESHOLD_CROSSING"
            elif adverse_direction:
                status = "ADVERSE_TREND_MONITOR"
            else:
                status = "NO_ADVERSE_TREND"
            metric_results.append({
                "metric": metric,
                "status": status,
                "observations": len(points),
                "latest_value": round(latest, 4),
                "projected_value": round(projected, 4),
                "daily_slope": round(slope, 6),
                "threshold": threshold,
                "forecast_date": (origin.fromordinal(origin.toordinal() + forecast_day)).isoformat(),
            })
        attention = sum(item["status"] in {"CURRENTLY_ADVERSE", "PROJECTED_THRESHOLD_CROSSING"} for item in metric_results)
        results.append({
            "project_id": project_id,
            "snapshot_count": len(rows),
            "attention_metric_count": attention,
            "metrics": metric_results,
        })

    return {
        "status": "ASSESSED" if results else "NO_SNAPSHOTS",
        "project_count": len(results),
        "horizon_days": horizon_days,
        "minimum_observations": minimum_observations,
        "projects": sorted(results, key=lambda row: (-row["attention_metric_count"], row["project_id"])),
        "method": "Ordinary least-squares linear extrapolation by calendar day.",
        "limitations": [
            "This is a transparent trend extrapolation, not machine learning, causal inference or a calibrated probability of failure.",
            "At least three valid dated observations are required separately for each metric.",
            "Forecast assumes a linear trend persists over the selected horizon; structural changes can invalidate it.",
            "No KPI values are imputed or clamped; inspect implausible projections before acting.",
            "Threshold crossings are review alerts only; management must validate source data and project context.",
        ],
    }
