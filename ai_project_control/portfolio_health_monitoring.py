"""Portfolio health monitoring based only on explicitly supplied dated snapshots.

No missing snapshot is inferred and no trend is calculated without a valid baseline.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _snapshot_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError("snapshot_date must be YYYY-MM-DD") from None


def build_health_monitoring(
    snapshots: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Compare each project’s latest two valid dated snapshots."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in snapshots:
        row = dict(raw)
        project_id = str(row.get("project_id", "")).strip()
        if not project_id:
            raise ValueError("project_id is required for every snapshot")
        observed = _snapshot_date(row.get("snapshot_date"))
        normalized = {
            "project_id": project_id,
            "project_name": str(row.get("project_name", "")).strip(),
            "snapshot_date": observed.isoformat(),
            "SPI": _finite(row.get("SPI")),
            "CPI": _finite(row.get("CPI")),
            "risk_score": _finite(row.get("risk_score")),
        }
        grouped.setdefault(project_id, []).append(normalized)

    results = []
    for project_id, rows in grouped.items():
        rows.sort(key=lambda item: item["snapshot_date"])
        # If multiple records exist on one date, do not silently choose one.
        by_date: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_date.setdefault(row["snapshot_date"], []).append(row)
        duplicates = [day for day, entries in by_date.items() if len(entries) > 1]
        if duplicates:
            results.append({
                "project_id": project_id,
                "project_name": rows[-1]["project_name"],
                "status": "DATA_CONFLICT",
                "data_conflicts": sorted(duplicates),
                "baseline_date": None,
                "latest_date": None,
                "changes": {},
                "signals": ["Multiple snapshots exist for the same project and date."],
            })
            continue

        unique_rows = list(by_date.values())
        ordered = [entries[0] for entries in unique_rows]
        latest = ordered[-1]
        if len(ordered) < 2:
            results.append({
                "project_id": project_id,
                "project_name": latest["project_name"],
                "status": "NO_BASELINE",
                "baseline_date": None,
                "latest_date": latest["snapshot_date"],
                "changes": {},
                "signals": ["A second dated snapshot is required before trend assessment."],
            })
            continue

        baseline = ordered[-2]
        changes: dict[str, float | None] = {}
        signals = []
        for metric in ("SPI", "CPI", "risk_score"):
            old, new = baseline[metric], latest[metric]
            changes[metric] = round(new - old, 4) if old is not None and new is not None else None
            if changes[metric] is None:
                signals.append(f"{metric} trend unavailable because one or both snapshots lack data.")
            elif metric in ("SPI", "CPI"):
                if changes[metric] < -0.02:
                    signals.append(f"{metric} deteriorated by {abs(changes[metric]):.3f}.")
                elif changes[metric] > 0.02:
                    signals.append(f"{metric} improved by {changes[metric]:.3f}.")
            else:
                if changes[metric] > 5:
                    signals.append(f"Risk score increased by {changes[metric]:.1f} points.")
                elif changes[metric] < -5:
                    signals.append(f"Risk score decreased by {abs(changes[metric]):.1f} points.")

        if all(value is None for value in changes.values()):
            status = "INSUFFICIENT_DATA"
        else:
            status = "TREND_ASSESSED"
        results.append({
            "project_id": project_id,
            "project_name": latest["project_name"] or baseline["project_name"],
            "status": status,
            "baseline_date": baseline["snapshot_date"],
            "latest_date": latest["snapshot_date"],
            "changes": changes,
            "signals": signals or ["No material movement detected using configured thresholds."],
        })

    results.sort(key=lambda item: (item["status"] != "DATA_CONFLICT", item["project_id"]))
    return {
        "projects": results,
        "summary": {
            "project_count": len(results),
            "trend_assessed_count": sum(row["status"] == "TREND_ASSESSED" for row in results),
            "no_baseline_count": sum(row["status"] == "NO_BASELINE" for row in results),
            "data_conflict_count": sum(row["status"] == "DATA_CONFLICT" for row in results),
            "insufficient_data_count": sum(row["status"] == "INSUFFICIENT_DATA" for row in results),
        },
        "method": (
            "Compares the latest two distinct supplied dates per project. SPI/CPI movement "
            "threshold is 0.02; risk movement threshold is 5 points. These are screening "
            "signals, not contractual or automated decisions."
        ),
    }
