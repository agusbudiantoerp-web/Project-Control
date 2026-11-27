"""Evidence-based project recovery intelligence for portfolio triage.

This module prioritizes review using supplied project-control indicators. It does
not infer root causes, generate ungrounded recovery quantities, or approve actions.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def _metric(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_project_recovery_intelligence(
    projects: Iterable[dict[str, Any]],
    *,
    actions: Iterable[dict[str, Any]] = (),
    monitoring_changes: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Create transparent triage tiers from known EVM, risk, delay and action data."""
    action_rows = list(actions)
    change_rows = list(monitoring_changes)
    results = []
    for project in projects:
        project_id = str(project.get("project_id", "")).strip()
        if not project_id:
            continue
        spi, cpi = _metric(project, "SPI"), _metric(project, "CPI")
        risk = _metric(project, "risk_score")
        delayed = _metric(project, "delayed_activity_count")
        overdue = _metric(project, "overdue_action_count")
        project_actions = [
            row for row in action_rows
            if str(row.get("project_id", "")).strip() == project_id
            and str(row.get("status", "")).upper() not in {"COMPLETED", "CANCELLED"}
        ]
        p1_open = sum(str(row.get("priority", "")).upper() == "P1" for row in project_actions)
        adverse_metrics = sorted({
            str(row.get("metric")) for row in change_rows
            if str(row.get("project_id", "")).strip() == project_id
            and str(row.get("change", "")).startswith("ADVERSE")
        })
        evidence = []
        if spi is not None and spi < 0.95:
            evidence.append("SPI_BELOW_0_95")
        if cpi is not None and cpi < 0.95:
            evidence.append("CPI_BELOW_0_95")
        if risk is not None and risk >= 75:
            evidence.append("HIGH_RISK_SCORE")
        if delayed is not None and delayed > 0:
            evidence.append("DELAYED_ACTIVITIES")
        if overdue is not None and overdue > 0:
            evidence.append("OVERDUE_ACTIONS")
        if p1_open:
            evidence.append("OPEN_P1_ACTIONS")
        if adverse_metrics:
            evidence.append("ADVERSE_MONITORING_CHANGE")

        missing = [
            key for key, value in (
                ("SPI", spi), ("CPI", cpi), ("risk_score", risk),
                ("delayed_activity_count", delayed), ("overdue_action_count", overdue),
            ) if value is None
        ]
        # Tiers reflect evidence presence, not a statistically calibrated prediction.
        critical = (
            (spi is not None and spi < 0.80)
            or (cpi is not None and cpi < 0.80)
            or (risk is not None and risk >= 90)
            or (p1_open > 0 and overdue is not None and overdue > 0)
        )
        watch = bool(evidence)
        tier = "CRITICAL_REVIEW" if critical else "RECOVERY_REVIEW" if watch else "NO_ADVERSE_SIGNAL"
        recommendations = []
        if spi is not None and spi < 0.95:
            recommendations.append("Validate critical-path status, remaining durations and schedule logic.")
        if cpi is not None and cpi < 0.95:
            recommendations.append("Reconcile actual cost, commitments, accruals and estimate to complete.")
        if risk is not None and risk >= 75:
            recommendations.append("Review top quantified risks, owners, response actions and contingency basis.")
        if delayed is not None and delayed > 0:
            recommendations.append("Validate delayed activities against approved baseline and current forecast.")
        if p1_open:
            recommendations.append("Review open P1 actions, accountable owners and due dates.")
        if adverse_metrics:
            recommendations.append("Investigate adverse snapshot changes: " + ", ".join(adverse_metrics) + ".")
        if missing:
            recommendations.append("Complete missing indicators before making a full recovery assessment.")
        if not recommendations:
            recommendations.append("Continue routine monitoring; no adverse signal is present in supplied indicators.")

        results.append({
            "project_id": project_id,
            "project_name": str(project.get("project_name", "")),
            "triage_tier": tier,
            "evidence_count": len(evidence),
            "evidence": evidence,
            "missing_indicators": missing,
            "open_p1_actions": p1_open,
            "adverse_monitoring_metrics": adverse_metrics,
            "recommended_reviews": recommendations,
            "decision_authority": "PROJECT_MANAGER / PROJECT_DIRECTOR",
        })

    order = {"CRITICAL_REVIEW": 0, "RECOVERY_REVIEW": 1, "NO_ADVERSE_SIGNAL": 2}
    results.sort(key=lambda row: (order[row["triage_tier"]], -row["evidence_count"], row["project_id"]))
    return {
        "status": "ASSESSED" if results else "NO_PROJECTS",
        "project_count": len(results),
        "critical_review_count": sum(row["triage_tier"] == "CRITICAL_REVIEW" for row in results),
        "recovery_review_count": sum(row["triage_tier"] == "RECOVERY_REVIEW" for row in results),
        "projects": results,
        "limitations": [
            "Triage tiers are transparent rule-based review priorities, not ML predictions or probability of failure.",
            "Missing indicators are disclosed and are never imputed as zero.",
            "Recommendations are review prompts; project leadership retains decision and approval authority.",
        ],
    }
