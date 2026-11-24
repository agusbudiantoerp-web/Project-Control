"""Risk exposure matrix with WBS/activity traceability and transparent mitigations."""
from __future__ import annotations

import math
from typing import Any

from .schedule_engine import calculate_critical_path


def _finite(value: Any, field: str, risk_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{risk_id}: {field} must be numeric") from None
    if not math.isfinite(number):
        raise ValueError(f"{risk_id}: {field} must be finite")
    return number


def _probability_band(value: float) -> str:
    if value < 0.30:
        return "LOW"
    if value < 0.60:
        return "MEDIUM"
    return "HIGH"


def _impact_band(value: float, low: float, high: float) -> str:
    if value < low:
        return "LOW"
    if value < high:
        return "MEDIUM"
    return "HIGH"


def _priority(probability: str, impact: str) -> str:
    score = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    product = score[probability] * score[impact]
    return "CRITICAL" if product >= 9 else "HIGH" if product >= 6 else "MODERATE" if product >= 3 else "LOW"


def _recommendation(row: dict[str, Any], critical: bool) -> str:
    supplied = str(row.get("mitigation", row.get("response_action", ""))).strip()
    if supplied:
        return supplied
    category = str(row.get("category", row.get("risk_category", ""))).strip().upper()
    if critical:
        return "Lakukan review segera dengan owner aktivitas kritis; tetapkan trigger, tindakan pencegahan, contingency, dan tanggal keputusan."
    if category in {"SAFETY", "HSE", "K3"}:
        return "Lakukan verifikasi HSE/JSA, kontrol lapangan, kompetensi, dan bukti inspeksi sebelum pekerjaan dilanjutkan."
    if category in {"COST", "FINANCE", "COMMERCIAL"}:
        return "Validasi kuantitas, harga, kontrak, cash flow, dan ambang eskalasi biaya."
    if category in {"SCHEDULE", "TIME", "DELAY"}:
        return "Periksa predecessor, float, kesiapan material, produktivitas, dan opsi recovery yang disetujui."
    if category in {"PROCUREMENT", "SUPPLY", "MATERIAL"}:
        return "Konfirmasi vendor, lead time, submittal, stok, dan alternatif pemasok yang telah disetujui."
    return "Tetapkan risk owner, trigger pemantauan, tindakan preventif, contingency, dan bukti penyelesaian."


def build_risk_exposure_matrix(
    risks: list[dict[str, Any]],
    *,
    activities: list[dict[str, Any]] | None = None,
    wbs: list[dict[str, Any]] | None = None,
    impact_medium_threshold: float = 1.0,
    impact_high_threshold: float = 5.0,
) -> dict[str, Any]:
    """Rank risk records using probability × impact and map IDs to project structure.

    Impact uses cost_impact_most_likely, else impact, else exposure. Values must
    be in one consistent unit for meaningful cross-risk ranking.
    """
    if not isinstance(risks, list) or any(not isinstance(row, dict) for row in risks):
        raise TypeError("risks must be a list of dictionaries")
    activities = activities or []
    wbs = wbs or []
    if not isinstance(activities, list) or not isinstance(wbs, list):
        raise TypeError("activities and wbs must be lists")
    medium = float(impact_medium_threshold)
    high = float(impact_high_threshold)
    if not math.isfinite(medium) or not math.isfinite(high) or medium < 0 or high <= medium:
        raise ValueError("impact thresholds must be finite with 0 <= medium < high")

    activity_ids = {str(row.get("activity_id", "")).strip() for row in activities if isinstance(row, dict)}
    wbs_ids = {str(row.get("wbs_id", "")).strip() for row in wbs if isinstance(row, dict)}
    has_complete_durations = bool(activities) and all(
        isinstance(row, dict) and row.get("duration_days") not in (None, "")
        for row in activities
    )
    cpm = (
        calculate_critical_path(activities)
        if has_complete_durations
        else {"status": "NO_ACTIVITIES" if not activities else "INSUFFICIENT_DATA", "activities": []}
    )
    critical_mapping_available = cpm.get("status") == "ASSESSED"
    critical_ids = {
        str(row["activity_id"]) for row in cpm.get("activities", [])
        if row.get("is_critical")
    } if critical_mapping_available else set()

    seen = set()
    ranked = []
    for index, row in enumerate(risks):
        rid = str(row.get("risk_id", "")).strip()
        if not rid:
            raise ValueError(f"Risk row {index + 1}: risk_id is required")
        if rid in seen:
            raise ValueError(f"{rid}: duplicate risk_id")
        seen.add(rid)
        probability = _finite(row.get("probability"), "probability", rid)
        impact_field = next((field for field in (
            "cost_impact_most_likely", "impact", "exposure"
        ) if row.get(field) not in (None, "")), None)
        if impact_field is None:
            raise ValueError(f"{rid}: one of cost_impact_most_likely, impact, or exposure is required")
        impact = _finite(row[impact_field], impact_field, rid)
        if not 0 <= probability <= 1 or impact < 0:
            raise ValueError(f"{rid}: probability must be 0..1 and impact must be non-negative")

        activity_id = str(row.get("activity_id", "")).strip()
        wbs_id = str(row.get("wbs_id", "")).strip()
        activity_known = not activity_id or activity_id in activity_ids
        wbs_known = not wbs_id or wbs_id in wbs_ids
        is_critical = bool(activity_id and activity_id in critical_ids)
        p_band = _probability_band(probability)
        i_band = _impact_band(impact, medium, high)
        expected_exposure = probability * impact
        priority = _priority(p_band, i_band)
        ranked.append({
            "risk_id": rid,
            "description": str(row.get("description", row.get("risk_description", ""))).strip(),
            "category": str(row.get("category", row.get("risk_category", ""))).strip(),
            "risk_owner": str(row.get("risk_owner", row.get("owner", ""))).strip(),
            "probability": probability,
            "probability_band": p_band,
            "impact": impact,
            "impact_field": impact_field,
            "impact_band": i_band,
            "expected_exposure": round(expected_exposure, 4),
            "priority": priority,
            "activity_id": activity_id or None,
            "activity_link_status": "UNLINKED" if not activity_id else "MATCHED" if activity_known else "UNKNOWN_ACTIVITY",
            "is_critical_activity": (
                None if activity_id and not activity_known
                else is_critical if critical_mapping_available
                else False if not activities
                else None
            ),
            "critical_mapping_status": cpm.get("status"),
            "wbs_id": wbs_id or None,
            "wbs_link_status": "UNLINKED" if not wbs_id else "MATCHED" if wbs_known else "UNKNOWN_WBS",
            "mitigation_recommendation": _recommendation(row, is_critical),
        })

    priority_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    ranked.sort(key=lambda item: (priority_order[item["priority"]], -item["expected_exposure"], item["risk_id"]))
    matrix = {
        probability: {
            impact: [row["risk_id"] for row in ranked
                     if row["probability_band"] == probability and row["impact_band"] == impact]
            for impact in ("HIGH", "MEDIUM", "LOW")
        }
        for probability in ("HIGH", "MEDIUM", "LOW")
    }
    return {
        "status": "ASSESSED" if ranked else "NO_RISKS",
        "risk_count": len(ranked),
        "priority_summary": {
            priority: sum(row["priority"] == priority for row in ranked)
            for priority in ("CRITICAL", "HIGH", "MODERATE", "LOW")
        },
        "critical_activity_risk_count": sum(row["is_critical_activity"] is True for row in ranked),
        "unlinked_activity_count": sum(row["activity_link_status"] != "MATCHED" for row in ranked),
        "unlinked_wbs_count": sum(row["wbs_link_status"] != "MATCHED" for row in ranked),
        "matrix": matrix,
        "risks": ranked,
        "caveats": [
            "Probability bands: LOW <30%, MEDIUM 30–59.99%, HIGH >=60%.",
            "Impact bands use the supplied numeric thresholds; all impacts must share one unit and currency for ranking.",
            "Expected exposure is probability × impact, not a forecast loss or a reserve.",
            "Unknown activity/WBS references are flagged; missing links are not inferred.",
            "Critical activity mapping is available only when the supplied activity network passes CPM validation.",
            "Recommendations are transparent rules or the mitigation text supplied in the risk register; management approval remains required.",
        ],
    }
