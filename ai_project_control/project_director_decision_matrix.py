"""Project Director decision matrix derived only from supplied portfolio evidence."""
from __future__ import annotations

import math
from typing import Any, Iterable


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def build_decision_matrix(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Rank projects for management review; missing evidence is explicitly surfaced."""
    rows = []
    for item in records:
        record = dict(item)
        spi, cpi = _number(record.get("SPI")), _number(record.get("CPI"))
        risk = _number(record.get("risk_score"))
        overload = _number(record.get("overloaded_resource_days"))
        gaps = [key for key, value in (("SPI", spi), ("CPI", cpi), ("risk_score", risk)) if value is None]

        # Evidence points: SPI/CPI below 0.95 = 3, below 1.0 = 2;
        # risk >=75 = 3, >=50 = 2, >=25 = 1; any positive resource overload = 1.
        points = 0
        if spi is not None:
            points += 3 if spi < 0.95 else 2 if spi < 1.0 else 0
        if cpi is not None:
            points += 3 if cpi < 0.95 else 2 if cpi < 1.0 else 0
        if risk is not None:
            points += 3 if risk >= 75 else 2 if risk >= 50 else 1 if risk >= 25 else 0
        if overload is not None and overload > 0:
            points += 1

        if len(gaps) == 3:
            priority = "UNASSESSED"
            action = "Collect SPI, CPI, and risk evidence before prioritization."
        elif points >= 6:
            priority = "P1"
            action = "Immediate Project Director review; validate recovery options and constraints."
        elif points >= 3:
            priority = "P2"
            action = "Assign an owner and recovery actions; review progress at the next control cycle."
        elif gaps:
            priority = "DATA_REVIEW"
            action = "Complete missing indicators before treating the project as stable."
        else:
            priority = "P3"
            action = "Continue routine monitoring and verify trends."
        rows.append({
            "project_id": str(record.get("project_id", "")),
            "project_name": str(record.get("project_name", "")),
            "priority": priority,
            "evidence_points": points,
            "SPI": spi,
            "CPI": cpi,
            "risk_score": risk,
            "overloaded_resource_days": overload,
            "data_gaps": gaps,
            "recommended_action": action,
        })

    order = {"P1": 0, "P2": 1, "DATA_REVIEW": 2, "P3": 3, "UNASSESSED": 4}
    rows.sort(key=lambda row: (order[row["priority"]], -row["evidence_points"], row["project_id"]))
    return {
        "decisions": rows,
        "summary": {
            "project_count": len(rows),
            "p1_count": sum(row["priority"] == "P1" for row in rows),
            "p2_count": sum(row["priority"] == "P2" for row in rows),
            "data_review_count": sum(row["priority"] == "DATA_REVIEW" for row in rows),
            "unassessed_count": sum(row["priority"] == "UNASSESSED" for row in rows),
        },
        "method": "SPI/CPI thresholds: <0.95 adds 3 points; <1.00 adds 2. Risk: >=75 adds 3, >=50 adds 2, >=25 adds 1. Positive overloaded resource days adds 1. This is a review-priority heuristic, not an automated approval.",
    }
