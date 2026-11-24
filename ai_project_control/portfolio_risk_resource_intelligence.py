"""Portfolio-wide risk and shared-resource exposure without currency/unit mixing."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def build_portfolio_risk_resource_view(
    project_risks: list[dict[str, Any]],
    project_resources: list[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(project_risks, list) or not isinstance(project_resources, list):
        raise TypeError("project_risks and project_resources must be lists")
    if any(not isinstance(row, dict) for row in project_risks + project_resources):
        raise TypeError("all portfolio records must be dictionaries")

    currency_totals: dict[str, float] = defaultdict(float)
    risk_rows = []
    unassessed_risks = []
    seen_risk_keys = set()
    for item in project_risks:
        project_id = str(item.get("project_id", "")).strip()
        risk_id = str(item.get("risk_id", "")).strip()
        currency = str(item.get("currency", "")).strip().upper()
        if not project_id or not risk_id:
            raise ValueError("each portfolio risk requires project_id and risk_id")
        key = (project_id, risk_id)
        if key in seen_risk_keys:
            raise ValueError(f"duplicate risk {project_id}/{risk_id}")
        seen_risk_keys.add(key)
        try:
            probability = float(item.get("probability"))
            impact = float(item.get("cost_impact_most_likely", item.get("impact", item.get("exposure"))))
        except (TypeError, ValueError):
            unassessed_risks.append({"project_id": project_id, "risk_id": risk_id, "reason": "Probability or impact missing/non-numeric"})
            continue
        if not math.isfinite(probability) or not 0 <= probability <= 1 or not math.isfinite(impact) or impact < 0:
            unassessed_risks.append({"project_id": project_id, "risk_id": risk_id, "reason": "Probability or impact outside valid range"})
            continue
        if not currency:
            unassessed_risks.append({"project_id": project_id, "risk_id": risk_id, "reason": "Currency missing; monetary exposure not aggregated"})
            continue
        exposure = probability * impact
        currency_totals[currency] += exposure
        risk_rows.append({
            "project_id": project_id, "risk_id": risk_id,
            "description": str(item.get("description", item.get("risk_description", ""))),
            "currency": currency, "probability": probability, "impact": impact,
            "expected_exposure": round(exposure, 4),
            "owner": str(item.get("risk_owner", item.get("owner", ""))),
        })

    risk_rows.sort(key=lambda row: (-row["expected_exposure"], row["currency"], row["project_id"], row["risk_id"]))

    # A shared-resource conflict is assessed only when all rows explicitly share
    # resource_id, period, unit, and the same declared capacity.
    buckets: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    unassessed_resources = []
    for item in project_resources:
        project_id = str(item.get("project_id", "")).strip()
        resource_id = str(item.get("resource_id", "")).strip()
        period = str(item.get("period", "")).strip()
        unit = str(item.get("unit", "")).strip()
        if not all((project_id, resource_id, period, unit)):
            unassessed_resources.append({"project_id": project_id, "resource_id": resource_id, "reason": "Project, resource, period or unit missing"})
            continue
        try:
            demand = float(item.get("planned_units"))
            capacity = float(item.get("capacity_units"))
        except (TypeError, ValueError):
            unassessed_resources.append({"project_id": project_id, "resource_id": resource_id, "reason": "Demand/capacity missing or non-numeric"})
            continue
        if not math.isfinite(demand) or demand < 0 or not math.isfinite(capacity) or capacity <= 0:
            unassessed_resources.append({"project_id": project_id, "resource_id": resource_id, "reason": "Demand/capacity invalid"})
            continue
        buckets[(resource_id, period, unit)].append({
            "project_id": project_id, "demand": demand, "capacity": capacity,
        })

    conflicts = []
    for (resource_id, period, unit), rows in sorted(buckets.items()):
        projects = sorted({row["project_id"] for row in rows})
        if len(projects) < 2:
            continue
        capacities = {row["capacity"] for row in rows}
        if len(capacities) != 1:
            unassessed_resources.append({
                "resource_id": resource_id, "period": period,
                "reason": "Shared capacity declarations conflict; no overload conclusion",
            })
            continue
        # Avoid double-counting duplicated rows for the same project/resource-period.
        by_project: dict[str, float] = defaultdict(float)
        for row in rows:
            by_project[row["project_id"]] += row["demand"]
        capacity = next(iter(capacities))
        total = sum(by_project.values())
        conflicts.append({
            "resource_id": resource_id, "period": period, "unit": unit,
            "projects": sorted(by_project),
            "project_count": len(by_project),
            "total_planned_demand": round(total, 4),
            "declared_capacity": capacity,
            "overload_units": round(max(0.0, total - capacity), 4),
            "status": "CROSS_PROJECT_OVERLOAD" if total > capacity else "WITHIN_SHARED_CAPACITY",
        })

    return {
        "status": "ASSESSED" if risk_rows or conflicts else "INSUFFICIENT_DATA",
        "risk_count_assessed": len(risk_rows),
        "risk_count_unassessed": len(unassessed_risks),
        "expected_exposure_by_currency": dict(sorted(currency_totals.items())),
        "top_risks": risk_rows[:20],
        "unassessed_risks": unassessed_risks,
        "shared_resource_period_count": len(conflicts),
        "shared_resource_conflict_count": sum(row["status"] == "CROSS_PROJECT_OVERLOAD" for row in conflicts),
        "shared_resource_conflicts": conflicts,
        "unassessed_resources": unassessed_resources,
        "limitations": [
            "Expected monetary exposure is probability × supplied impact, grouped by currency; currencies are never added together.",
            "Shared-resource overload is assessed only for exact resource ID, period, unit and consistent capacity matches across at least two projects.",
            "Resource IDs must represent the same real-world pool across projects; matching labels alone do not prove common ownership.",
            "No resource transfer, schedule change, mitigation, or risk acceptance is automatically approved.",
        ],
    }
