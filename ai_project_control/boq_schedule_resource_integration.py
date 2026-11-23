"""BOQ, schedule and resource crosswalk with explicit activity links."""
from __future__ import annotations

import math
from typing import Any

from .schedule_engine import calculate_critical_path


def _number(value: Any, field: str, row_id: str, *, required: bool = False) -> float | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{row_id}: {field} is required")
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{row_id}: {field} must be numeric") from None
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{row_id}: {field} must be finite and non-negative")
    return result


def build_boq_schedule_resource_integration(
    boq_rows: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    resource_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cross-reference BOQ quantities/cost, CPM durations and declared resources.

    BOQ/activity/resource relationships must use an explicit activity_id.
    No productivity, resource demand, calendar date or cost is inferred.
    """
    if not all(isinstance(rows, list) for rows in (boq_rows, activities, resource_rows)):
        raise TypeError("boq_rows, activities and resource_rows must be lists")
    cpm = calculate_critical_path(activities)
    if cpm["status"] not in {"ASSESSED", "NO_ACTIVITIES"}:
        return {"status": "INVALID_SCHEDULE", "schedule": cpm, "rows": [],
                "unlinked_boq": [], "unlinked_resources": [],
                "issues": cpm["issues"]}
    activity_map = {}
    for row in activities:
        activity_id = str(row.get("activity_id", "")).strip()
        if not activity_id:
            raise ValueError("Every activity requires activity_id")
        activity_map[activity_id] = row
    boq_by_activity: dict[str, dict[str, Any]] = {}
    unlinked_boq = []
    for index, row in enumerate(boq_rows):
        item_id = str(row.get("boq_id", f"BOQ-{index+1}")).strip()
        activity_id = str(row.get("activity_id", "")).strip()
        if not activity_id or activity_id not in activity_map:
            unlinked_boq.append(item_id)
            continue
        quantity = _number(row.get("quantity"), "quantity", item_id, required=True)
        rate = _number(row.get("unit_rate"), "unit_rate", item_id)
        amount = _number(row.get("amount"), "amount", item_id)
        if amount is None and rate is not None:
            amount = quantity * rate
        bucket = boq_by_activity.setdefault(activity_id, {
            "boq_item_count": 0, "boq_quantity": 0.0, "boq_amount": 0.0,
            "boq_amount_complete": True, "boq_units": set(), "quantity_by_unit": {}, "amount_by_currency": {}, "currencies": set(),
        })
        bucket["boq_item_count"] += 1
        unit = str(row.get("unit", row.get("uom", "UNSPECIFIED"))).strip() or "UNSPECIFIED"
        bucket["boq_units"].add(unit)
        bucket["quantity_by_unit"][unit] = bucket["quantity_by_unit"].get(unit, 0.0) + quantity
        currency = str(row.get("currency", "")).strip().upper()
        if amount is None or not currency:
            bucket["boq_amount_complete"] = False
        else:
            bucket["currencies"].add(currency)
            bucket["amount_by_currency"][currency] = bucket["amount_by_currency"].get(currency, 0.0) + amount

    resource_by_activity: dict[str, dict[str, Any]] = {}
    unlinked_resources = []
    for index, row in enumerate(resource_rows):
        resource_id = str(row.get("resource_id", f"RESOURCE-{index+1}")).strip()
        activity_id = str(row.get("activity_id", "")).strip()
        if not activity_id or activity_id not in activity_map:
            unlinked_resources.append(resource_id)
            continue
        demand = _number(row.get("planned_units"), "planned_units", resource_id, required=True)
        capacity = _number(row.get("capacity_units"), "capacity_units", resource_id)
        bucket = resource_by_activity.setdefault(activity_id, {
            "resource_count": 0, "planned_resource_units": 0.0,
            "capacity_complete": True, "capacity_by_resource": [],
            "resource_types": set(), "resource_units": set(), "demand_by_unit": {},
        })
        bucket["resource_count"] += 1
        unit = str(row.get("unit", "UNSPECIFIED")).strip() or "UNSPECIFIED"
        bucket["demand_by_unit"][unit] = bucket["demand_by_unit"].get(unit, 0.0) + demand
        bucket["capacity_by_resource"].append(capacity)
        if capacity is None:
            bucket["capacity_complete"] = False
        bucket["resource_types"].add(str(row.get("resource_type", "OTHER")).upper())
        bucket["resource_units"].add(unit)

    cpm_by_id = {row["activity_id"]: row for row in cpm.get("activities", [])}
    result_rows = []
    for activity_id, activity in activity_map.items():
        boq = boq_by_activity.get(activity_id)
        resources = resource_by_activity.get(activity_id)
        schedule = cpm_by_id.get(activity_id)
        result_rows.append({
            "activity_id": activity_id,
            "activity_name": str(activity.get("activity_name", activity.get("name", activity_id))),
            "duration_days": schedule.get("duration_days") if schedule else _number(activity.get("duration_days"), "duration_days", activity_id),
            "early_start_day": schedule.get("early_start") if schedule else None,
            "early_finish_day": schedule.get("early_finish") if schedule else None,
            "is_critical": schedule.get("is_critical") if schedule else None,
            "boq_item_count": boq["boq_item_count"] if boq else 0,
            "boq_quantity": round(next(iter(boq["quantity_by_unit"].values())), 3) if boq and len(boq["quantity_by_unit"]) == 1 else None,
            "boq_quantity_by_unit": "; ".join(f"{unit}: {value:g}" for unit, value in sorted(boq["quantity_by_unit"].items())) if boq else None,
            "boq_units": ", ".join(sorted(boq["boq_units"])) if boq else None,
            "boq_amount": round(next(iter(boq["amount_by_currency"].values())), 2) if boq and boq["boq_amount_complete"] and len(boq["currencies"]) == 1 else None,
            "boq_amount_by_currency": "; ".join(f"{currency}: {value:.2f}" for currency, value in sorted(boq["amount_by_currency"].items())) if boq else None,
            "resource_count": resources["resource_count"] if resources else 0,
            "planned_resource_units": round(next(iter(resources["demand_by_unit"].values())), 3) if resources and len(resources["demand_by_unit"]) == 1 else None,
            "planned_resource_units_by_unit": "; ".join(f"{unit}: {value:g}" for unit, value in sorted(resources["demand_by_unit"].items())) if resources else None,
            "resource_types": ", ".join(sorted(resources["resource_types"])) if resources else None,
            "resource_units": ", ".join(sorted(resources["resource_units"])) if resources else None,
            "status": "LINKED" if boq and resources and schedule else "PARTIAL_LINK",
        })
    return {
        "status": "ASSESSED" if result_rows and not unlinked_boq and not unlinked_resources else ("PARTIAL" if result_rows else "NO_LINKED_ACTIVITIES"),
        "schedule": cpm,
        "rows": result_rows,
        "unlinked_boq": unlinked_boq,
        "unlinked_resources": unlinked_resources,
        "limitations": [
            "BOQ items and resource assignments link to activities only through explicit activity_id.",
            "BOQ quantities and resource demand are never summed across unlike units; per-unit breakdowns are shown.",
            "BOQ amounts are shown only when currency is declared consistently; per-currency breakdowns are shown otherwise.",
            "CPM start/finish values are relative working-day offsets, not calendar dates.",
            "No productivity, resource requirement, unit rate, currency, shift pattern or approved schedule change is inferred.",
        ],
    }
