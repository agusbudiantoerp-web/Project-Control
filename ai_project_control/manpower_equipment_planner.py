"""Manpower and equipment capacity planning by resource class and unit."""
from __future__ import annotations

from typing import Any
import math
import pandas as pd

VALID_TYPES = {"MANPOWER", "EQUIPMENT", "MATERIAL", "OTHER"}


def build_manpower_equipment_plan(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize declared demand/capacity without inferring productivity or units.

    Each resource-period is kept separate by resource type and unit so, for
    example, operator-hours are never added to excavator-hours or headcount.
    """
    columns = [
        "resource_type", "resource_id", "resource_name", "unit", "period",
        "planned_units", "actual_units", "capacity_units",
        "planned_utilization_pct", "actual_utilization_pct", "status",
    ]
    if not records:
        return {"status": "NO_DATA", "rows": pd.DataFrame(columns=columns),
                "type_summary": pd.DataFrame(), "overloaded_count": 0,
                "unassessed_count": 0}
    frame = pd.DataFrame(records).copy()
    required = {"resource_id", "period", "planned_units", "capacity_units"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Resource records missing required fields: " + ", ".join(sorted(missing)))
    for optional, default in (("resource_type", "OTHER"), ("resource_name", ""),
                              ("unit", "UNSPECIFIED"), ("actual_units", pd.NA)):
        if optional not in frame:
            frame[optional] = default
    for field in ("resource_id", "period", "resource_type", "resource_name", "unit"):
        frame[field] = frame[field].fillna("").astype(str).str.strip()
    if frame[["resource_id", "period"]].eq("").any().any():
        raise ValueError("resource_id and period must be non-blank.")
    frame["resource_type"] = frame["resource_type"].str.upper().replace("", "OTHER")
    invalid_types = sorted(set(frame["resource_type"]) - VALID_TYPES)
    if invalid_types:
        raise ValueError("Unsupported resource_type values: " + ", ".join(invalid_types))
    frame["unit"] = frame["unit"].replace("", "UNSPECIFIED")
    for field in ("planned_units", "actual_units", "capacity_units"):
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        valid = frame[field].dropna()
        if (~valid.map(math.isfinite)).any() or (valid < 0).any():
            raise ValueError(field + " must contain finite, non-negative values.")

    keys = ["resource_type", "resource_id", "resource_name", "unit", "period"]
    grouped = frame.groupby(keys, as_index=False, dropna=False).agg(
        planned_units=("planned_units", "sum"),
        actual_units=("actual_units", lambda values: values.sum(min_count=1)),
        capacity_units=("capacity_units", "max"),
        capacity_consistent=("capacity_units", lambda values: values.dropna().nunique() <= 1),
        planned_complete=("planned_units", lambda values: values.notna().all()),
        actual_complete=("actual_units", lambda values: values.notna().all()),
        capacity_complete=("capacity_units", lambda values: values.notna().all()),
    )
    grouped["planned_utilization_pct"] = pd.NA
    grouped["actual_utilization_pct"] = pd.NA
    planned_ok = grouped["planned_complete"] & grouped["capacity_complete"] & grouped["capacity_consistent"] & grouped["capacity_units"].gt(0)
    actual_ok = grouped["actual_complete"] & grouped["capacity_complete"] & grouped["capacity_consistent"] & grouped["capacity_units"].gt(0)
    grouped.loc[planned_ok, "planned_utilization_pct"] = (
        grouped.loc[planned_ok, "planned_units"] / grouped.loc[planned_ok, "capacity_units"] * 100
    )
    grouped.loc[actual_ok, "actual_utilization_pct"] = (
        grouped.loc[actual_ok, "actual_units"] / grouped.loc[actual_ok, "capacity_units"] * 100
    )
    grouped["status"] = "WITHIN_CAPACITY"
    grouped.loc[~planned_ok, "status"] = "UNASSESSED"
    grouped.loc[planned_ok & grouped["planned_utilization_pct"].gt(100), "status"] = "OVERLOADED"
    output = grouped[keys + ["planned_units", "actual_units", "capacity_units",
                             "planned_utilization_pct", "actual_utilization_pct", "status"]]
    output = output.sort_values(["period", "resource_type", "resource_id"], kind="stable").reset_index(drop=True)
    type_summary = output.groupby("resource_type", as_index=False).agg(
        resource_periods=("resource_id", "count"),
        overloaded_periods=("status", lambda values: int(values.eq("OVERLOADED").sum())),
        unassessed_periods=("status", lambda values: int(values.eq("UNASSESSED").sum())),
    )
    return {
        "status": "ASSESSED" if output["status"].ne("UNASSESSED").any() else "UNASSESSED",
        "rows": output,
        "type_summary": type_summary,
        "overloaded_count": int(output["status"].eq("OVERLOADED").sum()),
        "unassessed_count": int(output["status"].eq("UNASSESSED").sum()),
        "limitations": [
            "Resource units and capacity must use the same unit and period basis.",
            "No shift pattern, productivity rate, overtime, or labor cost is inferred.",
            "A resource plan is a capacity check, not an approved assignment or schedule change.",
        ],
    }
