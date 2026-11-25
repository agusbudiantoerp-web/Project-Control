"""Cross-dataset validation for project-control workspaces.

This module validates supplied table-like records without modifying them or
assuming that absent data is zero. It is deliberately schema-light so it can
be adopted by CSV/Excel imports before a formal database schema exists.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

TABLE_KEYS = {
    "project_master": ("project_id",),
    "wbs": ("project_id", "wbs_id"),
    "boq": ("project_id", "boq_id"),
    "activities": ("project_id", "activity_id"),
    "progress": ("project_id", "activity_id", "period"),
    "actual_cost": ("project_id", "period", "cost_code"),
    "risk": ("project_id", "risk_id"),
    "resources": ("project_id", "resource_id", "period"),
    "portfolio_snapshots": ("project_id", "snapshot_date"),
    "schedule_baselines": ("project_id", "baseline_id"),
    "schedule_changes": ("project_id", "change_id"),
}
PROJECT_LINKED = tuple(name for name in TABLE_KEYS if name != "project_master")
NUMERIC_FIELDS = {
    "project_master": ("BAC", "bac", "budget_at_completion"),
    "boq": ("quantity", "unit_rate", "amount"),
    "activities": ("duration_days", "planned_duration_days", "actual_duration_days"),
    "progress": ("planned_value", "earned_value", "physical_progress_pct"),
    "actual_cost": ("actual_cost",),
    "risk": ("probability", "impact", "exposure", "risk_score", "cost_impact_min", "cost_impact_most_likely", "cost_impact_max"),
    "resources": ("planned_units", "actual_units", "capacity_units"),
    "portfolio_snapshots": ("SPI", "CPI", "risk_score"),
    "schedule_baselines": ("version",),
    "schedule_changes": ("cost_impact", "schedule_impact_days"),
}


def _rows(value: Any, table: str, issues: list[dict[str, str]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        issues.append({"severity": "ERROR", "code": "TABLE_NOT_A_LIST",
                       "table": table, "record": "", "field": "",
                       "message": f"{table} must be a list of records"})
        return []
    result = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            issues.append({"severity": "ERROR", "code": "ROW_NOT_A_RECORD",
                           "table": table, "record": str(index), "field": "",
                           "message": "Each row must be an object/dictionary"})
        else:
            result.append(dict(row))
    return result


def validate_project_control_data(tables: dict[str, Any]) -> dict[str, Any]:
    """Validate IDs, duplicate keys, project links, and numeric data fields."""
    if not isinstance(tables, dict):
        raise TypeError("tables must be a dictionary keyed by dataset name")

    issues: list[dict[str, str]] = []
    normalized = {name: _rows(tables.get(name), name, issues) for name in TABLE_KEYS}
    project_ids = set()
    for table, rows in normalized.items():
        key_fields = TABLE_KEYS[table]
        seen = set()
        for index, row in enumerate(rows):
            for field in key_fields:
                value = row.get(field)
                if value is None or str(value).strip() == "":
                    issues.append({"severity": "ERROR", "code": "MISSING_KEY",
                                   "table": table, "record": str(index), "field": field,
                                   "message": f"Required key {field} is missing"})
            key = tuple(str(row.get(field, "")).strip() for field in key_fields)
            if all(key) and key in seen:
                severity = "WARNING" if table == "portfolio_snapshots" else "ERROR"
                code = "DUPLICATE_SNAPSHOT_DATE" if table == "portfolio_snapshots" else "DUPLICATE_KEY"
                issues.append({"severity": severity, "code": code,
                               "table": table, "record": str(index), "field": ",".join(key_fields),
                               "message": f"Duplicate key: {' / '.join(key)}"})
            seen.add(key)
            if table == "project_master" and row.get("project_id") not in (None, ""):
                project_ids.add(str(row["project_id"]).strip())

            if table == "portfolio_snapshots":
                try:
                    from datetime import date
                    date.fromisoformat(str(row.get("snapshot_date", "")).strip())
                except (TypeError, ValueError):
                    issues.append({"severity": "ERROR", "code": "INVALID_SNAPSHOT_DATE",
                                   "table": table, "record": str(index), "field": "snapshot_date",
                                   "message": "snapshot_date must be a valid ISO date (YYYY-MM-DD)"})
            for field in NUMERIC_FIELDS.get(table, ()):
                raw = row.get(field)
                if raw in (None, ""):
                    continue
                try:
                    number = math.nan if isinstance(raw, bool) else float(raw)
                except (TypeError, ValueError):
                    number = math.nan
                if not math.isfinite(number):
                    issues.append({"severity": "ERROR", "code": "INVALID_NUMBER",
                                   "table": table, "record": str(index), "field": field,
                                   "message": f"{field} must be a finite number"})
                elif field == "probability" and not 0 <= number <= 1:
                    issues.append({"severity": "ERROR", "code": "PROBABILITY_OUT_OF_RANGE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": "probability must be between 0 and 1"})
                elif field == "risk_score" and not 0 <= number <= 100:
                    issues.append({"severity": "ERROR", "code": "RISK_SCORE_OUT_OF_RANGE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": "risk_score must be between 0 and 100"})
                elif field in {"SPI", "CPI"} and number < 0:
                    issues.append({"severity": "ERROR", "code": "NEGATIVE_PERFORMANCE_INDEX",
                                   "table": table, "record": str(index), "field": field,
                                   "message": f"{field} cannot be negative"})
                elif field == "physical_progress_pct" and not 0 <= number <= 100:
                    issues.append({"severity": "ERROR", "code": "PERCENT_OUT_OF_RANGE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": "physical_progress_pct must be between 0 and 100"})
                elif field in {"BAC", "bac", "budget_at_completion", "quantity", "unit_rate", "amount",
                               "planned_value", "earned_value", "actual_cost",
                               "duration_days", "planned_duration_days", "actual_duration_days",
                               "planned_units", "actual_units", "capacity_units", "impact",
                               "exposure", "cost_impact_min", "cost_impact_most_likely",
                               "cost_impact_max", "version", "cost_impact", "schedule_impact_days"} and number < 0:
                    issues.append({"severity": "ERROR", "code": "NEGATIVE_VALUE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": f"{field} cannot be negative"})

            if table == "project_master":
                for mode_field in ("progress_record_mode", "actual_cost_record_mode"):
                    raw_mode = row.get(mode_field)
                    if raw_mode not in (None, "") and str(raw_mode).strip() not in {
                        "period_delta", "cumulative_snapshot"
                    }:
                        issues.append({
                            "severity": "ERROR", "code": "INVALID_EVM_RECORD_MODE",
                            "table": table, "record": str(index), "field": mode_field,
                            "message": f"{mode_field} must be period_delta or cumulative_snapshot",
                        })

            if table == "boq":
                raw_quantity = row.get("quantity")
                raw_unit_rate = row.get("unit_rate")
                raw_amount = row.get("amount")
                if all(value not in (None, "") for value in (
                    raw_quantity, raw_unit_rate, raw_amount
                )):
                    try:
                        quantity = float(raw_quantity)
                        unit_rate = float(raw_unit_rate)
                        amount = float(raw_amount)
                    except (TypeError, ValueError, OverflowError):
                        pass  # Field-level numeric checks above report invalid values.
                    else:
                        if all(math.isfinite(value) for value in (
                            quantity, unit_rate, amount
                        )):
                            expected_amount = quantity * unit_rate
                            if not math.isclose(
                                amount, expected_amount, rel_tol=1e-6, abs_tol=0.01
                            ):
                                issues.append({
                                    "severity": "ERROR",
                                    "code": "BOQ_AMOUNT_MISMATCH",
                                    "table": table,
                                    "record": str(index),
                                    "field": "amount",
                                    "message": (
                                        "amount must equal quantity multiplied by unit_rate "
                                        "(tolerance: 0.01 currency unit or 0.0001%)."
                                    ),
                                })

    if normalized["project_master"]:
        for table in PROJECT_LINKED:
            for index, row in enumerate(normalized[table]):
                project_id = str(row.get("project_id", "")).strip()
                if project_id and project_id not in project_ids:
                    issues.append({"severity": "ERROR", "code": "UNKNOWN_PROJECT",
                                   "table": table, "record": str(index), "field": "project_id",
                                   "message": f"Project {project_id} is not present in project_master"})


    # Validate explicit cross-table links within each project. Optional links are
    # checked only when the source row supplies the corresponding identifier.
    def add_link_issue(code: str, table: str, index: int, field: str, message: str) -> None:
        issues.append({
            "severity": "ERROR", "code": code, "table": table,
            "record": str(index), "field": field, "message": message,
        })

    def project_index(table: str, id_field: str) -> dict[str, dict[str, Any]]:
        result = {}
        for row in normalized[table]:
            pid = str(row.get("project_id", "")).strip()
            identity = str(row.get(id_field, "")).strip()
            if pid and identity and identity not in result.setdefault(pid, {}):
                result[pid][identity] = row
        return result

    wbs_by_project = project_index("wbs", "wbs_id")
    activities_by_project = project_index("activities", "activity_id")
    boq_by_project = project_index("boq", "boq_id")

    # WBS parent links must exist and the hierarchy must be acyclic.
    for index, row in enumerate(normalized["wbs"]):
        pid = str(row.get("project_id", "")).strip()
        wbs_id = str(row.get("wbs_id", "")).strip()
        parent = str(row.get("parent_wbs_id", "") or "").strip()
        known_wbs = wbs_by_project.get(pid, {})
        if parent and parent not in known_wbs:
            add_link_issue("UNKNOWN_WBS_PARENT", "wbs", index, "parent_wbs_id",
                           f"Parent WBS {parent} does not exist in project {pid}")
        if parent and parent == wbs_id:
            add_link_issue("WBS_SELF_PARENT", "wbs", index, "parent_wbs_id",
                           f"WBS {wbs_id} cannot be its own parent")

    for pid, records in wbs_by_project.items():
        for start_id in records:
            visited = set()
            current = start_id
            while current in records:
                if current in visited:
                    add_link_issue("WBS_HIERARCHY_CYCLE", "wbs", 0, "parent_wbs_id",
                                   f"WBS hierarchy contains a cycle in project {pid}: {current}")
                    break
                visited.add(current)
                parent = str(records[current].get("parent_wbs_id", "") or "").strip()
                if not parent or parent not in records:
                    break
                current = parent

    # Activity WBS and predecessor references must resolve in the same project.
    for index, row in enumerate(normalized["activities"]):
        pid = str(row.get("project_id", "")).strip()
        wbs_id = str(row.get("wbs_id", "") or "").strip()
        if wbs_id and pid in wbs_by_project and wbs_id not in wbs_by_project[pid]:
            add_link_issue("UNKNOWN_ACTIVITY_WBS", "activities", index, "wbs_id",
                           f"Activity WBS {wbs_id} does not exist in project {pid}")
        raw_predecessors = row.get("predecessor_ids", row.get("predecessors"))
        if raw_predecessors in (None, ""):
            predecessors = []
        elif isinstance(raw_predecessors, (list, tuple, set)):
            predecessors = [str(value.get("activity_id", "") if isinstance(value, dict) else value).strip()
                            for value in raw_predecessors]
        else:
            predecessors = [value.strip() for value in str(raw_predecessors).replace(";", ",").split(",")]
        known_activities = activities_by_project.get(pid, {})
        for predecessor in filter(None, predecessors):
            if predecessor == str(row.get("activity_id", "")).strip():
                add_link_issue("ACTIVITY_SELF_PREDECESSOR", "activities", index, "predecessor_ids",
                               f"Activity {predecessor} cannot depend on itself")
            elif pid in activities_by_project and predecessor not in known_activities:
                add_link_issue("UNKNOWN_ACTIVITY_PREDECESSOR", "activities", index, "predecessor_ids",
                               f"Predecessor activity {predecessor} does not exist in project {pid}")

    # BOQ, progress, actual-cost and resource links are validated when supplied.
    for index, row in enumerate(normalized["boq"]):
        pid = str(row.get("project_id", "")).strip()
        wbs_id = str(row.get("wbs_id", "") or "").strip()
        activity_id = str(row.get("activity_id", "") or "").strip()
        if wbs_id and pid in wbs_by_project and wbs_id not in wbs_by_project[pid]:
            add_link_issue("UNKNOWN_BOQ_WBS", "boq", index, "wbs_id",
                           f"BOQ WBS {wbs_id} does not exist in project {pid}")
        if activity_id and pid in activities_by_project and activity_id not in activities_by_project[pid]:
            add_link_issue("UNKNOWN_BOQ_ACTIVITY", "boq", index, "activity_id",
                           f"BOQ activity {activity_id} does not exist in project {pid}")
        activity = activities_by_project.get(pid, {}).get(activity_id)
        if activity and wbs_id and str(activity.get("wbs_id", "") or "").strip() and wbs_id != str(activity.get("wbs_id")).strip():
            add_link_issue("BOQ_ACTIVITY_WBS_MISMATCH", "boq", index, "activity_id",
                           f"BOQ {row.get('boq_id')} and activity {activity_id} belong to different WBS elements")

    for index, row in enumerate(normalized["progress"]):
        pid = str(row.get("project_id", "")).strip()
        activity_id = str(row.get("activity_id", "") or "").strip()
        boq_id = str(row.get("boq_id", "") or "").strip()
        if activity_id and pid in activities_by_project and activity_id not in activities_by_project[pid]:
            add_link_issue("UNKNOWN_PROGRESS_ACTIVITY", "progress", index, "activity_id",
                           f"Progress activity {activity_id} does not exist in project {pid}")
        if boq_id and pid in boq_by_project and boq_id not in boq_by_project[pid]:
            add_link_issue("UNKNOWN_PROGRESS_BOQ", "progress", index, "boq_id",
                           f"Progress BOQ {boq_id} does not exist in project {pid}")
        activity = activities_by_project.get(pid, {}).get(activity_id)
        boq = boq_by_project.get(pid, {}).get(boq_id)
        if activity and boq:
            activity_wbs = str(activity.get("wbs_id", "") or "").strip()
            boq_wbs = str(boq.get("wbs_id", "") or "").strip()
            if activity_wbs and boq_wbs and activity_wbs != boq_wbs:
                add_link_issue("PROGRESS_ACTIVITY_BOQ_WBS_MISMATCH", "progress", index, "boq_id",
                               f"Progress activity {activity_id} and BOQ {boq_id} belong to different WBS elements")

    for index, row in enumerate(normalized["actual_cost"]):
        pid = str(row.get("project_id", "")).strip()
        boq_id = str(row.get("boq_id", "") or "").strip()
        wbs_id = str(row.get("wbs_id", "") or "").strip()
        if boq_id and pid in boq_by_project and boq_id not in boq_by_project[pid]:
            add_link_issue("UNKNOWN_COST_BOQ", "actual_cost", index, "boq_id",
                           f"Actual-cost BOQ {boq_id} does not exist in project {pid}")
        if wbs_id and pid in wbs_by_project and wbs_id not in wbs_by_project[pid]:
            add_link_issue("UNKNOWN_COST_WBS", "actual_cost", index, "wbs_id",
                           f"Actual-cost WBS {wbs_id} does not exist in project {pid}")
        boq = boq_by_project.get(pid, {}).get(boq_id)
        if boq and wbs_id and str(boq.get("wbs_id", "") or "").strip() and wbs_id != str(boq.get("wbs_id")).strip():
            add_link_issue("COST_BOQ_WBS_MISMATCH", "actual_cost", index, "wbs_id",
                           f"Actual cost BOQ {boq_id} and WBS {wbs_id} do not match")

    for index, row in enumerate(normalized["resources"]):
        pid = str(row.get("project_id", "")).strip()
        activity_id = str(row.get("activity_id", "") or "").strip()
        if activity_id and pid in activities_by_project and activity_id not in activities_by_project[pid]:
            add_link_issue("UNKNOWN_RESOURCE_ACTIVITY", "resources", index, "activity_id",
                           f"Resource activity {activity_id} does not exist in project {pid}")

    # Baseline snapshots are versioned project records. Change requests may
    # reference only a baseline belonging to the same project.
    baselines_by_project = project_index("schedule_baselines", "baseline_id")
    for index, row in enumerate(normalized["schedule_baselines"]):
        version = row.get("version")
        if version not in (None, ""):
            try:
                numeric_version = float(version)
            except (TypeError, ValueError, OverflowError):
                numeric_version = math.nan
            if not math.isfinite(numeric_version) or numeric_version < 1 or not numeric_version.is_integer():
                add_link_issue("INVALID_BASELINE_VERSION", "schedule_baselines", index, "version",
                               "Baseline version must be a positive integer")
        snapshot = row.get("activities_snapshot")
        if snapshot is not None:
            if not isinstance(snapshot, list):
                add_link_issue("INVALID_BASELINE_SNAPSHOT", "schedule_baselines", index,
                               "activities_snapshot", "activities_snapshot must be a list")
            else:
                seen_snapshot_ids = set()
                for activity_index, activity in enumerate(snapshot):
                    if not isinstance(activity, dict):
                        add_link_issue("INVALID_BASELINE_ACTIVITY", "schedule_baselines", index,
                                       "activities_snapshot",
                                       f"Baseline activity at position {activity_index} must be an object")
                        continue
                    activity_id = str(activity.get("activity_id", "")).strip()
                    if not activity_id:
                        add_link_issue("MISSING_BASELINE_ACTIVITY_ID", "schedule_baselines", index,
                                       "activities_snapshot",
                                       f"Baseline activity at position {activity_index} has no activity_id")
                    elif activity_id in seen_snapshot_ids:
                        add_link_issue("DUPLICATE_BASELINE_ACTIVITY_ID", "schedule_baselines", index,
                                       "activities_snapshot",
                                       f"Baseline snapshot contains duplicate activity {activity_id}")
                    seen_snapshot_ids.add(activity_id)

    for index, row in enumerate(normalized["schedule_changes"]):
        pid = str(row.get("project_id", "")).strip()
        baseline_id = str(row.get("baseline_id", "") or "").strip()
        if baseline_id and normalized["schedule_baselines"] and baseline_id not in baselines_by_project.get(pid, {}):
            add_link_issue("UNKNOWN_CHANGE_BASELINE", "schedule_changes", index, "baseline_id",
                           f"Schedule change references unknown baseline {baseline_id} in project {pid}")

    errors = sum(issue["severity"] == "ERROR" for issue in issues)
    warnings = sum(issue["severity"] == "WARNING" for issue in issues)
    row_count = sum(len(rows) for rows in normalized.values())
    return {
        "status": "INVALID" if errors else ("VALID_WITH_WARNINGS" if warnings else "VALID"),
        "table_count": len(TABLE_KEYS),
        "record_count": row_count,
        "error_count": errors,
        "warning_count": warnings,
        "issues": issues,
        "validated_tables": {name: len(rows) for name, rows in normalized.items()},
        "limitations": [
            "Only the supplied records and declared checks are validated.",
            "An empty optional dataset is not evidence that the project has no activity, cost, risk or resource demand.",
            "Business-specific BOQ, schedule, EVM and risk rules require an approved project data dictionary.",
        ],
    }
