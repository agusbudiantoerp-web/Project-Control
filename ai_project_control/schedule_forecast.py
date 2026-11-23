"""Schedule variance and finish-date delay assessment from explicit date/progress inputs."""
from __future__ import annotations

from datetime import date
from typing import Any


def _date(value: Any, field: str, activity_id: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError(f"Activity {activity_id}: {field} must be an ISO date (YYYY-MM-DD)") from None


def _percent(value: Any, field: str, activity_id: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Activity {activity_id}: {field} must be numeric") from None
    if not 0 <= number <= 100:
        raise ValueError(f"Activity {activity_id}: {field} must be between 0 and 100")
    return number


def assess_schedule_delays(
    activities: list[dict[str, Any]],
    *,
    as_of_date: str | date,
    warning_threshold_days: int = 1,
    progress_warning_threshold_pp: float = 5.0,
) -> dict[str, Any]:
    """Assess activity variance and explicit finish-date forecast delays.

    Recognized fields: activity_id, baseline_finish_date, forecast_finish_date,
    planned_progress_pct, actual_progress_pct. No forecast date is inferred
    from incomplete progress data.
    """
    if not isinstance(activities, list):
        raise TypeError("activities must be a list")
    if warning_threshold_days < 0 or progress_warning_threshold_pp < 0:
        raise ValueError("warning thresholds must be non-negative")
    if isinstance(as_of_date, date):
        as_of = as_of_date
    else:
        try:
            as_of = date.fromisoformat(str(as_of_date)[:10])
        except ValueError:
            raise ValueError("as_of_date must be YYYY-MM-DD") from None

    seen = set()
    assessed = []
    unassessed = []
    delayed = []
    for index, row in enumerate(activities):
        if not isinstance(row, dict):
            raise TypeError(f"Activity at index {index} must be a dictionary")
        activity_id = str(row.get("activity_id", "")).strip()
        if not activity_id:
            raise ValueError(f"Activity at index {index}: activity_id is required")
        if activity_id in seen:
            raise ValueError(f"Duplicate activity_id: {activity_id}")
        seen.add(activity_id)

        baseline = _date(row.get("baseline_finish_date"), "baseline_finish_date", activity_id)
        forecast = _date(row.get("forecast_finish_date"), "forecast_finish_date", activity_id)
        planned = _percent(row.get("planned_progress_pct"), "planned_progress_pct", activity_id)
        actual = _percent(row.get("actual_progress_pct"), "actual_progress_pct", activity_id)

        variance_pp = actual - planned if actual is not None and planned is not None else None
        delay_days = (forecast - baseline).days if forecast is not None and baseline is not None else None
        if delay_days is not None:
            status = "DELAYED" if delay_days > warning_threshold_days else (
                "AHEAD" if delay_days < -warning_threshold_days else "ON_TRACK"
            )
        elif variance_pp is not None:
            status = "BEHIND_PROGRESS" if variance_pp < -progress_warning_threshold_pp else (
                "AHEAD_PROGRESS" if variance_pp > progress_warning_threshold_pp else "PROGRESS_ON_TRACK"
            )
        else:
            status = "INSUFFICIENT_DATA"

        result = {
            "activity_id": activity_id,
            "activity_name": str(row.get("activity_name", row.get("name", activity_id))),
            "baseline_finish_date": baseline.isoformat() if baseline else None,
            "forecast_finish_date": forecast.isoformat() if forecast else None,
            "delay_days": delay_days,
            "planned_progress_pct": planned,
            "actual_progress_pct": actual,
            "progress_variance_pp": round(variance_pp, 2) if variance_pp is not None else None,
            "status": status,
            "as_of_date": as_of.isoformat(),
        }
        assessed.append(result)
        if status == "DELAYED" or status == "BEHIND_PROGRESS":
            delayed.append(activity_id)
        if status == "INSUFFICIENT_DATA":
            unassessed.append(activity_id)

    dated_forecasts = [item for item in assessed if item["forecast_finish_date"]]
    project_forecast = max(
        (item["forecast_finish_date"] for item in dated_forecasts),
        default=None,
    )
    dated_baselines = [item for item in assessed if item["baseline_finish_date"]]
    project_baseline = max(
        (item["baseline_finish_date"] for item in dated_baselines),
        default=None,
    )
    project_delay = None
    if project_forecast and project_baseline and len(dated_forecasts) == len(assessed) and len(dated_baselines) == len(assessed):
        project_delay = (date.fromisoformat(project_forecast) - date.fromisoformat(project_baseline)).days

    return {
        "status": "ASSESSED" if assessed and not unassessed else (
            "PARTIALLY_ASSESSED" if assessed else "NO_ACTIVITIES"
        ),
        "as_of_date": as_of.isoformat(),
        "activity_count": len(assessed),
        "delayed_activity_ids": delayed,
        "unassessed_activity_ids": unassessed,
        "project_baseline_finish_date": project_baseline if len(dated_baselines) == len(assessed) and assessed else None,
        "project_forecast_finish_date": project_forecast if len(dated_forecasts) == len(assessed) and assessed else None,
        "project_delay_days": project_delay,
        "activities": assessed,
        "limitations": [
            "Finish-date forecasts must be supplied; no forecast is inferred from progress percentages.",
            "Progress variance is a percentage-point comparison, not a duration forecast.",
            "Dates use calendar-day differences; working calendars, holidays and contractual rules are not applied.",
            "A project finish is reported only when every listed activity has both baseline and forecast finish dates.",
        ],
    }
