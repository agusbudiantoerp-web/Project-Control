"""What-if transfer impact analysis for shared resources across projects."""
from __future__ import annotations

from typing import Any
import pandas as pd


def simulate_resource_transfer_impact(
    resource_summary: dict[str, Any],
    project_priorities: dict[str, float] | None = None,
    donor_release_pct: float = 10.0,
) -> dict[str, Any]:
    """Simulate shifting an explicitly capped share of donor allocation.

    Capacity is conserved: every unit transferred to a recipient is removed
    from a donor's allocation for the same shared resource and date. The
    scenario is advisory and never edits source assignments or dates.
    """
    if not 0 <= float(donor_release_pct) <= 50:
        raise ValueError("donor_release_pct must be between 0 and 50.")
    daily = resource_summary.get("daily_load")
    details = resource_summary.get("resources")
    empty = pd.DataFrame()
    if not isinstance(daily, pd.DataFrame) or daily.empty or not isinstance(details, pd.DataFrame) or details.empty:
        return {"available": False, "impact": empty, "transfers": empty, "summary": empty,
                "assumptions": ["No portfolio resource loading data is available."]}
    required_daily = {"project_id", "rsrc_id", "date", "demand_per_day"}
    required_details = {"project_id", "rsrc_id", "shared_resource_id", "capacity_per_day"}
    if required_daily - set(daily.columns) or required_details - set(details.columns):
        return {"available": False, "impact": empty, "transfers": empty, "summary": empty,
                "assumptions": ["Required daily demand or shared-resource metadata is missing."]}

    mapping = details[list(required_details)].copy()
    mapping["shared_resource_id"] = mapping["shared_resource_id"].fillna("").astype(str).str.strip()
    mapping = mapping[mapping["shared_resource_id"] != ""].drop_duplicates(["project_id", "rsrc_id"])
    joined = daily.merge(mapping, on=["project_id", "rsrc_id"], how="inner", suffixes=("", "_meta"))
    if joined.empty:
        return {"available": False, "impact": empty, "transfers": empty, "summary": empty,
                "assumptions": ["No explicitly shared resource demand was found."]}

    priorities = project_priorities or {}
    joined["project_id"] = joined["project_id"].astype(str)
    joined["priority_score"] = joined["project_id"].map(lambda p: float(priorities.get(p, 0.0)))
    joined["demand_per_day"] = pd.to_numeric(joined["demand_per_day"], errors="coerce").fillna(0).clip(lower=0)
    joined["capacity_per_day_meta"] = pd.to_numeric(joined["capacity_per_day_meta"], errors="coerce")
    impact_rows, transfer_rows = [], []

    for (shared_id, day), group in joined.groupby(["shared_resource_id", "date"], dropna=False):
        capacities = group["capacity_per_day_meta"].dropna().unique()
        if len(capacities) == 0:
            continue
        capacity = float(min(capacities))
        projects = group.groupby("project_id", as_index=False).agg(
            demand=("demand_per_day", "sum"),
            priority=("priority_score", "max"),
            resource_name=("resource_name", "first") if "resource_name" in group else ("rsrc_id", "first"),
        )
        projects = projects.sort_values(["priority", "project_id"], ascending=[False, True]).reset_index(drop=True)
        remaining = capacity
        projects["baseline_allocated"] = 0.0
        for idx, row in projects.iterrows():
            allocated = min(float(row["demand"]), max(0.0, remaining))
            projects.loc[idx, "baseline_allocated"] = allocated
            remaining -= allocated
        projects["scenario_allocated"] = projects["baseline_allocated"]
        recipients = projects.index[projects["demand"] > projects["baseline_allocated"]].tolist()
        donors = projects.index[projects["baseline_allocated"] > 0].tolist()
        for recipient_idx in recipients:
            recipient_need = float(projects.loc[recipient_idx, "demand"] - projects.loc[recipient_idx, "scenario_allocated"])
            for donor_idx in sorted(donors, key=lambda i: (float(projects.loc[i, "priority"]), str(projects.loc[i, "project_id"]))):
                if donor_idx == recipient_idx or recipient_need <= 1e-9:
                    continue
                donor = projects.loc[donor_idx]
                # Only lower-priority projects can donate to a higher-priority recipient.
                if float(donor["priority"]) >= float(projects.loc[recipient_idx, "priority"]):
                    continue
                release_cap = float(donor["baseline_allocated"]) * float(donor_release_pct) / 100.0
                already_released = float(donor["baseline_allocated"] - donor["scenario_allocated"])
                releasable = max(0.0, release_cap - already_released)
                moved = min(releasable, recipient_need, float(projects.loc[donor_idx, "scenario_allocated"]))
                if moved <= 1e-9:
                    continue
                projects.loc[donor_idx, "scenario_allocated"] -= moved
                projects.loc[recipient_idx, "scenario_allocated"] += moved
                recipient_need -= moved
                transfer_rows.append({
                    "shared_resource_id": str(shared_id), "date": str(day),
                    "donor_project_id": str(donor["project_id"]),
                    "recipient_project_id": str(projects.loc[recipient_idx, "project_id"]),
                    "resource_name": str(donor["resource_name"]),
                    "transferred_per_day": moved,
                    "donor_priority": float(donor["priority"]),
                    "recipient_priority": float(projects.loc[recipient_idx, "priority"]),
                })
        for _, row in projects.iterrows():
            baseline_unmet = max(0.0, float(row["demand"] - row["baseline_allocated"]))
            scenario_unmet = max(0.0, float(row["demand"] - row["scenario_allocated"]))
            impact_rows.append({
                "shared_resource_id": str(shared_id), "date": str(day),
                "project_id": str(row["project_id"]), "resource_name": str(row["resource_name"]),
                "priority_score": float(row["priority"]), "demand_per_day": float(row["demand"]),
                "baseline_allocated_per_day": float(row["baseline_allocated"]),
                "scenario_allocated_per_day": float(row["scenario_allocated"]),
                "baseline_unmet_per_day": baseline_unmet, "scenario_unmet_per_day": scenario_unmet,
                "allocation_change_per_day": float(row["scenario_allocated"] - row["baseline_allocated"]),
                "donor_impact": max(0.0, float(row["baseline_allocated"] - row["scenario_allocated"])),
                "recipient_benefit": max(0.0, float(row["scenario_allocated"] - row["baseline_allocated"])),
                "capacity_per_day": capacity,
            })

    impact = pd.DataFrame(impact_rows)
    transfers = pd.DataFrame(transfer_rows)
    if impact.empty:
        return {"available": False, "impact": empty, "transfers": empty, "summary": empty,
                "assumptions": ["No valid shared-resource capacity could be evaluated."]}
    summary = impact.groupby("project_id").agg(
        resource_days=("date", "nunique"),
        baseline_unmet=("baseline_unmet_per_day", "sum"),
        scenario_unmet=("scenario_unmet_per_day", "sum"),
        allocation_change=("allocation_change_per_day", "sum"),
        donor_impact=("donor_impact", "sum"),
        recipient_benefit=("recipient_benefit", "sum"),
    ).reset_index()
    summary["net_unmet_change"] = summary["scenario_unmet"] - summary["baseline_unmet"]
    total_baseline = float(impact["baseline_unmet_per_day"].sum())
    total_scenario = float(impact["scenario_unmet_per_day"].sum())
    return {
        "available": True, "impact": impact, "transfers": transfers, "summary": summary,
        "metrics": {
            "baseline_unmet": total_baseline,
            "scenario_unmet": total_scenario,
            "unmet_reduction": total_baseline - total_scenario,
            "transferred_units": float(transfers["transferred_per_day"].sum()) if not transfers.empty else 0.0,
            "capacity_conserved": bool((impact.groupby(["shared_resource_id", "date"])["scenario_allocated_per_day"].sum() <= impact.groupby(["shared_resource_id", "date"])["capacity_per_day"].first() + 1e-9).all()),
        },
        "assumptions": [
            "Only explicitly shared_resource_id pools are considered; unrelated resources are never mixed.",
            "Baseline allocation is priority-first, using risk score and project ID as a stable tie-breaker.",
            "Only lower-priority projects can donate to a higher-priority recipient.",
            "Donor release is capped at the user-selected percentage of the donor's baseline allocation.",
            "Every transferred unit is removed from the donor and assigned to the recipient on the same date; total physical capacity is conserved.",
            "The simulation does not move task dates, change productivity, or approve an operational transfer.",
        ],
    }
