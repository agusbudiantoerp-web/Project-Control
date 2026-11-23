"""Deterministic, non-destructive cross-project shared-resource allocation scenarios."""
from __future__ import annotations

from typing import Any
import pandas as pd


def build_resource_allocation_scenario(
    resource_summary: dict[str, Any],
    project_priorities: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Allocate each shared resource-day by descending project priority.

    Higher priority scores receive capacity first. The engine only creates a
    recommendation register; it never edits source assignments or baselines.
    Resource capacity is the lowest declared capacity for a shared physical ID.
    """
    daily = resource_summary.get("daily_load")
    details = resource_summary.get("resources")
    columns = [
        "shared_resource_id", "date", "project_id", "resource_name",
        "priority_score", "demand_per_day", "allocated_per_day",
        "unmet_demand_per_day", "capacity_per_day", "utilization_after_pct",
        "allocation_status", "recommendation",
    ]
    empty = pd.DataFrame(columns=columns)
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        return {"available": False, "allocations": empty, "summary": pd.DataFrame(),
                "assumptions": ["No daily resource loading data is available."]}

    required_daily = {"project_id", "rsrc_id", "date", "demand_per_day"}
    required_details = {"project_id", "rsrc_id", "shared_resource_id", "capacity_per_day"}
    if required_daily - set(daily.columns) or not isinstance(details, pd.DataFrame) or required_details - set(details.columns):
        return {"available": False, "allocations": empty, "summary": pd.DataFrame(),
                "assumptions": ["Required project-scoped daily loading or shared-resource metadata is missing."]}

    mapping = details[list(required_details)].copy()
    mapping["shared_resource_id"] = mapping["shared_resource_id"].fillna("").astype(str).str.strip()
    mapping = mapping[mapping["shared_resource_id"] != ""].drop_duplicates(["project_id", "rsrc_id"])
    if mapping.empty:
        return {"available": False, "allocations": empty, "summary": pd.DataFrame(),
                "assumptions": ["No explicitly shared physical resources were identified."]}

    joined = daily.merge(mapping, on=["project_id", "rsrc_id"], how="inner", suffixes=("", "_meta"))
    if joined.empty:
        return {"available": False, "allocations": empty, "summary": pd.DataFrame(),
                "assumptions": ["No daily demand rows matched shared-resource identities."]}

    priorities = project_priorities or {}
    joined["priority_score"] = joined["project_id"].astype(str).map(
        lambda project_id: float(priorities.get(project_id, 0.0))
    )
    joined["demand_per_day"] = pd.to_numeric(joined["demand_per_day"], errors="coerce").fillna(0).clip(lower=0)
    joined["capacity_per_day"] = pd.to_numeric(joined["capacity_per_day_meta"], errors="coerce")
    rows = []
    for (shared_id, day), group in joined.groupby(["shared_resource_id", "date"], dropna=False):
        capacities = group["capacity_per_day"].dropna().unique()
        if len(capacities) == 0:
            continue
        capacity = float(min(capacities))
        remaining = capacity
        # Highest score first; stable project ID tie-breaker.
        group = group.sort_values(["priority_score", "project_id"], ascending=[False, True])
        for item in group.itertuples():
            demand = float(item.demand_per_day)
            allocated = min(demand, max(0.0, remaining))
            remaining -= allocated
            unmet = max(0.0, demand - allocated)
            if unmet <= 1e-9:
                status = "Fully allocated"
                recommendation = "Keep current allocation"
            elif allocated > 1e-9:
                status = "Partially allocated"
                recommendation = "Reschedule remaining demand or add verified capacity"
            else:
                status = "Not allocated"
                recommendation = "Re-sequence work or source additional shared capacity"
            rows.append({
                "shared_resource_id": str(shared_id), "date": str(day),
                "project_id": str(item.project_id),
                "resource_name": str(getattr(item, "resource_name", item.rsrc_id)),
                "priority_score": float(item.priority_score),
                "demand_per_day": demand, "allocated_per_day": allocated,
                "unmet_demand_per_day": unmet, "capacity_per_day": capacity,
                "utilization_after_pct": allocated / capacity * 100 if capacity > 0 else None,
                "allocation_status": status, "recommendation": recommendation,
            })

    allocations = pd.DataFrame(rows, columns=columns)
    if allocations.empty:
        return {"available": False, "allocations": empty, "summary": pd.DataFrame(),
                "assumptions": ["No valid shared-resource demand could be allocated."]}
    summary = allocations.groupby("shared_resource_id", dropna=False).agg(
        dates=("date", "nunique"),
        projects=("project_id", "nunique"),
        total_demand=("demand_per_day", "sum"),
        total_allocated=("allocated_per_day", "sum"),
        total_unmet=("unmet_demand_per_day", "sum"),
        peak_unmet_per_day=("unmet_demand_per_day", "max"),
    ).reset_index()
    summary["allocation_status"] = summary["total_unmet"].apply(
        lambda value: "Capacity shortfall" if value > 1e-9 else "Within shared capacity"
    )
    return {
        "available": True,
        "allocations": allocations,
        "summary": summary,
        "assumptions": [
            "Higher project priority score receives shared capacity first; ties are resolved by project ID.",
            "Capacity is not duplicated across projects and uses the lowest declared capacity for a shared ID.",
            "The scenario is advisory and does not alter assignments, CPM dates, baselines, or source datasets.",
            "Critical-path and contractual constraints must be verified before applying any proposed transfer.",
        ],
    }
