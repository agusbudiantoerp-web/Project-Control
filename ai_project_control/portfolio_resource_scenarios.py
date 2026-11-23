"""Compare transparent allocation policies for shared cross-project resources."""
from __future__ import annotations

from typing import Any
import pandas as pd


def _waterfill(demands: list[float], weights: list[float], capacity: float) -> list[float]:
    """Allocate capacity proportionally to weights without exceeding demand."""
    allocations = [0.0] * len(demands)
    remaining = max(0.0, float(capacity))
    active = {i for i, demand in enumerate(demands) if demand > 0}
    while active and remaining > 1e-9:
        total_weight = sum(max(weights[i], 1e-9) for i in active)
        proposed = {i: remaining * max(weights[i], 1e-9) / total_weight for i in active}
        capped = [i for i in active if proposed[i] >= demands[i] - allocations[i] - 1e-9]
        if not capped:
            for i in active:
                allocations[i] += proposed[i]
            remaining = 0.0
            break
        for i in capped:
            take = max(0.0, demands[i] - allocations[i])
            allocations[i] += take
            remaining -= take
            active.remove(i)
    return allocations


def compare_resource_allocation_scenarios(
    resource_summary: dict[str, Any],
    project_priorities: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compare priority-first, equal-fair-share, and risk-weighted allocation.

    These are advisory what-if distributions over the same declared shared
    capacity and demand. They do not move assignments or alter project data.
    """
    daily = resource_summary.get("daily_load")
    details = resource_summary.get("resources")
    empty = pd.DataFrame()
    if not isinstance(daily, pd.DataFrame) or daily.empty or not isinstance(details, pd.DataFrame) or details.empty:
        return {"available": False, "comparison": empty, "allocations": empty,
                "assumptions": ["No resource loading data is available."]}
    required_daily = {"project_id", "rsrc_id", "date", "demand_per_day"}
    required_details = {"project_id", "rsrc_id", "shared_resource_id", "capacity_per_day"}
    if required_daily - set(daily.columns) or required_details - set(details.columns):
        return {"available": False, "comparison": empty, "allocations": empty,
                "assumptions": ["Required resource demand or shared-resource metadata is missing."]}

    mapping = details[list(required_details)].copy()
    mapping["shared_resource_id"] = mapping["shared_resource_id"].fillna("").astype(str).str.strip()
    mapping = mapping[mapping["shared_resource_id"] != ""].drop_duplicates(["project_id", "rsrc_id"])
    joined = daily.merge(mapping, on=["project_id", "rsrc_id"], how="inner", suffixes=("", "_meta"))
    if joined.empty:
        return {"available": False, "comparison": empty, "allocations": empty,
                "assumptions": ["No explicitly shared resource demand was found."]}

    priorities = project_priorities or {}
    joined["project_id"] = joined["project_id"].astype(str)
    joined["priority_score"] = joined["project_id"].map(
        lambda project_id: max(0.0, float(priorities.get(project_id, 0.0)))
    )
    joined["demand_per_day"] = pd.to_numeric(joined["demand_per_day"], errors="coerce").fillna(0).clip(lower=0)
    joined["capacity_per_day_meta"] = pd.to_numeric(joined["capacity_per_day_meta"], errors="coerce")
    rows = []
    for (shared_id, day), group in joined.groupby(["shared_resource_id", "date"], dropna=False):
        caps = group["capacity_per_day_meta"].dropna().unique()
        if len(caps) == 0:
            continue
        capacity = float(min(caps))
        # Multiple records for one project/resource/day are consolidated.
        projects = group.groupby("project_id", as_index=False).agg(
            demand=("demand_per_day", "sum"),
            priority=("priority_score", "max"),
            resource_name=("resource_name", "first") if "resource_name" in group else ("rsrc_id", "first"),
        ).sort_values("project_id")
        demands = projects["demand"].astype(float).tolist()
        scores = projects["priority"].astype(float).tolist()
        policies = {
            "Priority first": None,
            "Equal fair share": [1.0 for _ in demands],
            "Risk-weighted share": [1.0 + score / 100.0 for score in scores],
        }
        for policy, weights in policies.items():
            if policy == "Priority first":
                order = sorted(range(len(demands)), key=lambda i: (-scores[i], str(projects.iloc[i]["project_id"])))
                allocation = [0.0] * len(demands)
                remaining = capacity
                for i in order:
                    allocation[i] = min(demands[i], remaining)
                    remaining -= allocation[i]
            else:
                allocation = _waterfill(demands, weights, capacity)
            for i, project in projects.iterrows():
                allocated = min(float(demands[i]), max(0.0, allocation[i]))
                unmet = max(0.0, float(demands[i]) - allocated)
                rows.append({
                    "scenario": policy, "shared_resource_id": str(shared_id), "date": str(day),
                    "project_id": str(project["project_id"]), "resource_name": str(project["resource_name"]),
                    "priority_score": float(project["priority"]), "demand_per_day": float(demands[i]),
                    "allocated_per_day": allocated, "unmet_demand_per_day": unmet,
                    "capacity_per_day": capacity,
                    "utilization_after_pct": allocated / capacity * 100 if capacity > 0 else None,
                })
    allocations = pd.DataFrame(rows)
    if allocations.empty:
        return {"available": False, "comparison": empty, "allocations": empty,
                "assumptions": ["No valid shared resource capacity could be evaluated."]}
    comparison = allocations.groupby("scenario").agg(
        project_days=("project_id", "count"),
        total_demand=("demand_per_day", "sum"),
        total_allocated=("allocated_per_day", "sum"),
        total_unmet=("unmet_demand_per_day", "sum"),
        project_days_with_shortfall=("unmet_demand_per_day", lambda x: int((x > 1e-9).sum())),
        maximum_daily_shortfall=("unmet_demand_per_day", "max"),
    ).reset_index()
    comparison["weighted_unmet"] = allocations.assign(
        weighted=allocations["unmet_demand_per_day"] * (1 + allocations["priority_score"] / 100)
    ).groupby("scenario")["weighted"].sum().reindex(comparison["scenario"]).to_numpy()
    comparison["projects_fully_served"] = allocations.assign(
        full=allocations["unmet_demand_per_day"] <= 1e-9
    ).groupby("scenario").apply(
        lambda frame: frame.loc[frame["full"], "project_id"].nunique()
    ).reindex(comparison["scenario"]).to_numpy()
    return {
        "available": True, "comparison": comparison, "allocations": allocations,
        "assumptions": [
            "Priority first serves higher risk-score projects first; ties are alphabetical by project ID.",
            "Equal fair share distributes constrained capacity proportionally to daily demand.",
            "Risk-weighted share gives greater proportional weight to projects with higher risk scores.",
            "Capacity is the lowest declared capacity for each shared physical resource ID and date.",
            "These are alternative advisory distributions, not approved transfers or updated assignments.",
        ],
    }
