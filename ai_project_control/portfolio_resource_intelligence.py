"""Portfolio-level resource loading summaries with project-scoped resource identities."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_portfolio_resource_summary(projects: list[dict]) -> dict:
    """Summarize resource demand by project and resource.

    Resource IDs are scoped to each project unless a shared_resource_id is
    explicitly supplied. This avoids falsely treating identically named IDs
    in separate projects as the same physical crew or equipment.
    """
    detail_rows = []
    daily_rows = []
    for project in projects:
        project_id = str(project.get("project_id", "")).strip()
        project_name = str(project.get("project_name", project_id)).strip()
        resources = project.get("resources")
        assignments = project.get("assignments")
        if not isinstance(resources, pd.DataFrame) or not isinstance(assignments, pd.DataFrame):
            continue
        if resources.empty or assignments.empty:
            continue
        required_r = {"rsrc_id", "capacity_per_day"}
        required_a = {"rsrc_id", "target_qty", "target_start_date", "target_end_date"}
        if required_r - set(resources.columns) or required_a - set(assignments.columns):
            continue
        resource_frame = resources.copy()
        assignment_frame = assignments.copy()
        resource_frame["rsrc_id"] = resource_frame["rsrc_id"].astype(str).str.strip()
        assignment_frame["rsrc_id"] = assignment_frame["rsrc_id"].astype(str).str.strip()
        resource_frame["capacity_per_day"] = pd.to_numeric(resource_frame["capacity_per_day"], errors="coerce")
        capacity_map = dict(zip(resource_frame["rsrc_id"], resource_frame["capacity_per_day"]))
        name_map = dict(zip(resource_frame["rsrc_id"], resource_frame.get("rsrc_name", resource_frame["rsrc_id"])))
        type_map = dict(zip(resource_frame["rsrc_id"], resource_frame.get("rsrc_type", pd.Series("Unclassified", index=resource_frame.index))))
        for resource_id, rows in assignment_frame.groupby("rsrc_id"):
            capacity = capacity_map.get(resource_id)
            if pd.isna(capacity) or not np.isfinite(capacity) or capacity <= 0:
                continue
            daily = {}
            valid_assignments = 0
            for row in rows.itertuples():
                qty = pd.to_numeric(pd.Series([getattr(row, "target_qty", None)]), errors="coerce").iloc[0]
                start = pd.to_datetime(getattr(row, "target_start_date", None), errors="coerce")
                finish = pd.to_datetime(getattr(row, "target_end_date", None), errors="coerce")
                if pd.isna(qty) or qty < 0 or pd.isna(start) or pd.isna(finish) or finish < start:
                    continue
                days = pd.date_range(start.normalize(), finish.normalize(), freq="D")
                if len(days) == 0:
                    continue
                valid_assignments += 1
                per_day = float(qty) / len(days)
                for day in days:
                    daily[day] = daily.get(day, 0.0) + per_day
            if not valid_assignments:
                continue
            peak = max(daily.values(), default=0.0)
            utilization = peak / float(capacity) * 100.0
            overload_days = sum(value > float(capacity) + 1e-9 for value in daily.values())
            shared_id = None
            if "shared_resource_id" in resource_frame.columns:
                match = resource_frame.loc[resource_frame["rsrc_id"] == resource_id, "shared_resource_id"]
                if not match.empty and pd.notna(match.iloc[0]) and str(match.iloc[0]).strip():
                    shared_id = str(match.iloc[0]).strip()
            detail_rows.append({
                "project_id": project_id, "project_name": project_name,
                "rsrc_id": resource_id, "resource_name": name_map.get(resource_id, resource_id),
                "resource_type": type_map.get(resource_id, "Unclassified"),
                "capacity_per_day": float(capacity), "peak_demand_per_day": peak,
                "peak_utilization_pct": utilization, "overloaded_days": overload_days,
                "assignments_count": valid_assignments,
                "capacity_status": "Over capacity" if overload_days else ("High utilization" if utilization >= 80 else "Within capacity"),
                "shared_resource_id": shared_id or "",
            })
            for day, demand in daily.items():
                daily_rows.append({
                    "project_id": project_id, "project_name": project_name,
                    "rsrc_id": resource_id, "resource_name": name_map.get(resource_id, resource_id),
                    "resource_type": type_map.get(resource_id, "Unclassified"),
                    "date": day.date().isoformat(), "demand_per_day": demand,
                    "capacity_per_day": float(capacity),
                    "utilization_pct": utilization if capacity == 0 else demand / float(capacity) * 100.0,
                    "over_capacity": demand > float(capacity) + 1e-9,
                })
    detail = pd.DataFrame(detail_rows)
    daily = pd.DataFrame(daily_rows)
    if detail.empty:
        project_summary = pd.DataFrame(columns=[
            "project_id", "project_name", "resources_tracked", "overloaded_resources",
            "overloaded_resource_days", "peak_utilization_pct"
        ])
    else:
        project_summary = detail.groupby(["project_id", "project_name"], dropna=False).agg(
            resources_tracked=("rsrc_id", "nunique"),
            overloaded_resources=("overloaded_days", lambda values: int((values > 0).sum())),
            overloaded_resource_days=("overloaded_days", "sum"),
            peak_utilization_pct=("peak_utilization_pct", "max"),
        ).reset_index()
        project_summary = project_summary.sort_values(
            ["overloaded_resources", "peak_utilization_pct"], ascending=[False, False]
        )
    return {"available": not detail.empty, "resources": detail, "daily_load": daily,
            "project_summary": project_summary}


def detect_shared_resource_conflicts(resource_summary: dict) -> dict:
    """Detect cross-project contention for explicitly shared physical resources.

    Capacity is treated as one shared pool, not added once per project. If
    projects declare different capacities for the same shared ID, the lowest
    declared capacity is used conservatively and the mismatch is flagged.
    """
    daily = resource_summary.get("daily_load")
    details = resource_summary.get("resources")
    if not isinstance(daily, pd.DataFrame) or daily.empty or not isinstance(details, pd.DataFrame) or details.empty:
        empty = pd.DataFrame(columns=[
            "shared_resource_id", "date", "projects", "demand_per_day",
            "capacity_per_day", "utilization_pct", "over_capacity", "capacity_mismatch"
        ])
        return {"available": False, "daily_conflicts": empty, "summary": empty.copy()}

    shared_ids = details[["project_id", "rsrc_id", "shared_resource_id", "capacity_per_day"]].copy()
    shared_ids["shared_resource_id"] = shared_ids["shared_resource_id"].fillna("").astype(str).str.strip()
    shared_ids = shared_ids[shared_ids["shared_resource_id"] != ""]
    if shared_ids.empty:
        empty = pd.DataFrame(columns=[
            "shared_resource_id", "date", "projects", "demand_per_day",
            "capacity_per_day", "utilization_pct", "over_capacity", "capacity_mismatch"
        ])
        return {"available": False, "daily_conflicts": empty, "summary": empty.copy()}

    shared_daily = daily.merge(
        shared_ids[["project_id", "rsrc_id", "shared_resource_id", "capacity_per_day"]],
        on=["project_id", "rsrc_id"], how="inner", suffixes=("", "_declared")
    )
    if shared_daily.empty:
        empty = pd.DataFrame(columns=[
            "shared_resource_id", "date", "projects", "demand_per_day",
            "capacity_per_day", "utilization_pct", "over_capacity", "capacity_mismatch"
        ])
        return {"available": False, "daily_conflicts": empty, "summary": empty.copy()}

    output = []
    for shared_id, rows in shared_daily.groupby("shared_resource_id"):
        capacities = pd.to_numeric(rows["capacity_per_day_declared"], errors="coerce").dropna().unique()
        if len(capacities) == 0:
            continue
        capacity_mismatch = len(capacities) > 1
        capacity = float(min(capacities))
        for day, day_rows in rows.groupby("date"):
            demand = float(day_rows["demand_per_day"].sum())
            project_ids = sorted(day_rows["project_id"].astype(str).unique().tolist())
            output.append({
                "shared_resource_id": shared_id,
                "date": day,
                "projects": ", ".join(project_ids),
                "project_count": len(project_ids),
                "demand_per_day": demand,
                "capacity_per_day": capacity,
                "utilization_pct": demand / capacity * 100.0 if capacity > 0 else np.nan,
                "over_capacity": demand > capacity + 1e-9,
                "capacity_mismatch": capacity_mismatch,
            })
    conflicts = pd.DataFrame(output)
    if conflicts.empty:
        return {"available": False, "daily_conflicts": conflicts, "summary": conflicts.copy()}
    summary = conflicts.groupby("shared_resource_id", dropna=False).agg(
        project_count=("project_count", "max"),
        overloaded_days=("over_capacity", "sum"),
        peak_demand_per_day=("demand_per_day", "max"),
        capacity_per_day=("capacity_per_day", "min"),
        peak_utilization_pct=("utilization_pct", "max"),
        capacity_mismatch=("capacity_mismatch", "max"),
    ).reset_index()
    summary["allocation_status"] = summary.apply(
        lambda row: "Capacity mismatch - verify" if row["capacity_mismatch"] else
        ("Cross-project conflict" if row["overloaded_days"] > 0 else "Within shared capacity"),
        axis=1,
    )
    return {"available": True, "daily_conflicts": conflicts, "summary": summary}
