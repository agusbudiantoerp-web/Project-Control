"""Transparent resource loading summary from stored workspace resource records."""
from __future__ import annotations

from typing import Any
import math
import pandas as pd


def build_resource_loading_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate planned/actual units against declared capacity by resource and period.

    Missing capacity or demand remains unassessed; no zero-capacity assumptions
    or inferred resource productivity are introduced.
    """
    columns = ["resource_id", "period", "planned_units", "actual_units",
               "capacity_units", "planned_utilization_pct", "actual_utilization_pct",
               "status"]
    if not records:
        return {"status": "NO_DATA", "rows": pd.DataFrame(columns=columns),
                "overloaded_count": 0, "unassessed_count": 0}
    frame = pd.DataFrame(records).copy()
    required = {"resource_id", "period", "planned_units", "capacity_units"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Resource records missing required fields: " + ", ".join(sorted(missing)))
    frame["resource_id"] = frame["resource_id"].astype("string").str.strip()
    frame["period"] = frame["period"].astype("string").str.strip()
    if frame[["resource_id", "period"]].isna().any().any() or frame["resource_id"].eq("").any() or frame["period"].eq("").any():
        raise ValueError("resource_id and period must be non-blank.")
    for field in ("planned_units", "actual_units", "capacity_units"):
        if field not in frame:
            frame[field] = pd.NA
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
        valid = frame[field].dropna()
        if (~valid.map(math.isfinite)).any() or (valid < 0).any():
            raise ValueError(field + " must contain finite, non-negative values.")
    grouped = frame.groupby(["resource_id", "period"], as_index=False, dropna=False).agg(
        planned_units=("planned_units", "sum"),
        actual_units=("actual_units", lambda values: values.sum(min_count=1)),
        capacity_units=("capacity_units", "sum"),
    )
    # A missing demand/capacity on any contributing record makes the aggregate
    # incomplete rather than silently treating missing records as zero.
    completeness = frame.groupby(["resource_id", "period"], as_index=False).agg(
        planned_complete=("planned_units", lambda values: values.notna().all()),
        capacity_complete=("capacity_units", lambda values: values.notna().all()),
        actual_complete=("actual_units", lambda values: values.notna().all()),
    )
    grouped = grouped.merge(completeness, on=["resource_id", "period"], how="left")
    grouped["planned_utilization_pct"] = pd.NA
    grouped["actual_utilization_pct"] = pd.NA
    planned_ok = grouped["planned_complete"] & grouped["capacity_complete"] & grouped["capacity_units"].gt(0)
    actual_ok = grouped["actual_complete"] & grouped["capacity_complete"] & grouped["capacity_units"].gt(0)
    grouped.loc[planned_ok, "planned_utilization_pct"] = (
        grouped.loc[planned_ok, "planned_units"] / grouped.loc[planned_ok, "capacity_units"] * 100
    )
    grouped.loc[actual_ok, "actual_utilization_pct"] = (
        grouped.loc[actual_ok, "actual_units"] / grouped.loc[actual_ok, "capacity_units"] * 100
    )
    grouped["status"] = "WITHIN_CAPACITY"
    grouped.loc[~planned_ok, "status"] = "UNASSESSED"
    grouped.loc[planned_ok & grouped["planned_utilization_pct"].gt(100), "status"] = "OVERLOADED"
    output = grouped[columns].sort_values(["period", "resource_id"], kind="stable").reset_index(drop=True)
    return {
        "status": "ASSESSED" if output["status"].ne("UNASSESSED").any() else "UNASSESSED",
        "rows": output,
        "overloaded_count": int(output["status"].eq("OVERLOADED").sum()),
        "unassessed_count": int(output["status"].eq("UNASSESSED").sum()),
    }
