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
}
PROJECT_LINKED = tuple(name for name in TABLE_KEYS if name != "project_master")
NUMERIC_FIELDS = {
    "boq": ("quantity", "unit_rate", "amount"),
    "activities": ("duration_days", "planned_duration_days", "actual_duration_days"),
    "progress": ("planned_value", "earned_value", "physical_progress_pct"),
    "actual_cost": ("actual_cost",),
    "risk": ("probability", "impact", "exposure", "cost_impact_min", "cost_impact_most_likely", "cost_impact_max"),
    "resources": ("planned_units", "actual_units", "capacity_units"),
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
                issues.append({"severity": "ERROR", "code": "DUPLICATE_KEY",
                               "table": table, "record": str(index), "field": ",".join(key_fields),
                               "message": f"Duplicate key: {' / '.join(key)}"})
            seen.add(key)
            if table == "project_master" and row.get("project_id") not in (None, ""):
                project_ids.add(str(row["project_id"]).strip())

            for field in NUMERIC_FIELDS.get(table, ()):
                raw = row.get(field)
                if raw in (None, ""):
                    continue
                try:
                    number = float(raw)
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
                elif field == "physical_progress_pct" and not 0 <= number <= 100:
                    issues.append({"severity": "ERROR", "code": "PERCENT_OUT_OF_RANGE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": "physical_progress_pct must be between 0 and 100"})
                elif field in {"quantity", "unit_rate", "amount", "duration_days",
                               "planned_duration_days", "actual_duration_days",
                               "planned_units", "actual_units", "capacity_units", "impact", "exposure", "cost_impact_min", "cost_impact_most_likely", "cost_impact_max"} and number < 0:
                    issues.append({"severity": "ERROR", "code": "NEGATIVE_VALUE",
                                   "table": table, "record": str(index), "field": field,
                                   "message": f"{field} cannot be negative"})

    if normalized["project_master"]:
        for table in PROJECT_LINKED:
            for index, row in enumerate(normalized[table]):
                project_id = str(row.get("project_id", "")).strip()
                if project_id and project_id not in project_ids:
                    issues.append({"severity": "ERROR", "code": "UNKNOWN_PROJECT",
                                   "table": table, "record": str(index), "field": "project_id",
                                   "message": f"Project {project_id} is not present in project_master"})

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
