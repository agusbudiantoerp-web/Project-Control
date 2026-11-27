"""Executive recovery decision brief from existing, separately assessed engines.

This module consolidates evidence and review prompts; it does not select or
approve an intervention, merge independent Monte Carlo distributions, or
infer causality.
"""
from __future__ import annotations

import math
from typing import Any


def _number(value: Any, field: str) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def build_recovery_decision_brief(
    *,
    evm: dict[str, Any] | None = None,
    risk_exposure: dict[str, Any] | None = None,
    risk_adjusted_outlook: dict[str, Any] | None = None,
    scenario_comparison: dict[str, Any] | None = None,
    resource_recovery: dict[str, Any] | None = None,
    spi_warning_threshold: float = 0.95,
    cpi_warning_threshold: float = 0.95,
) -> dict[str, Any]:
    """Create a traceable executive brief from optional engine result payloads."""
    inputs = {
        "evm": evm,
        "risk_exposure": risk_exposure,
        "risk_adjusted_outlook": risk_adjusted_outlook,
        "scenario_comparison": scenario_comparison,
        "resource_recovery": resource_recovery,
    }
    for name, value in inputs.items():
        if value is not None and not isinstance(value, dict):
            raise TypeError(f"{name} must be a dictionary or None")

    spi_limit = _number(spi_warning_threshold, "spi_warning_threshold")
    cpi_limit = _number(cpi_warning_threshold, "cpi_warning_threshold")
    if spi_limit is None or cpi_limit is None or not 0 < spi_limit <= 1 or not 0 < cpi_limit <= 1:
        raise ValueError("SPI/CPI warning thresholds must be between 0 and 1")

    signals: list[dict[str, Any]] = []
    recommendations: list[str] = []
    missing: list[str] = []

    if evm is None:
        missing.append("EVM")
    else:
        spi = _number(evm.get("SPI"), "evm.SPI")
        cpi = _number(evm.get("CPI"), "evm.CPI")
        if spi is None:
            missing.append("SPI")
        elif spi < spi_limit:
            signals.append({"code": "SCHEDULE_PERFORMANCE_BELOW_THRESHOLD", "severity": "HIGH" if spi < 0.80 else "MEDIUM", "value": spi})
            recommendations.append("Validasi critical path, remaining duration, predecessor, dan forecast finish sebelum menyetujui recovery jadwal.")
        if cpi is None:
            missing.append("CPI")
        elif cpi < cpi_limit:
            signals.append({"code": "COST_PERFORMANCE_BELOW_THRESHOLD", "severity": "HIGH" if cpi < 0.80 else "MEDIUM", "value": cpi})
            recommendations.append("Rekonsiliasi actual cost, commitments, accruals, dan estimate-to-complete sebelum menyetujui tambahan biaya.")

    if risk_exposure is None:
        missing.append("RISK_REGISTER")
    else:
        summary = risk_exposure.get("priority_summary") or {}
        critical = int(summary.get("CRITICAL", 0) or 0)
        high = int(summary.get("HIGH", 0) or 0)
        if critical:
            signals.append({"code": "CRITICAL_RISKS_OPEN", "severity": "HIGH", "count": critical})
            recommendations.append("Lakukan review risiko CRITICAL bersama risk owner; pastikan trigger, contingency, due date, dan approval tercatat.")
        if high:
            signals.append({"code": "HIGH_RISKS_OPEN", "severity": "MEDIUM", "count": high})
            recommendations.append("Tinjau risiko HIGH dan pastikan mitigasi memiliki owner serta bukti pelaksanaan.")
        if risk_exposure.get("status") == "NO_RISKS":
            missing.append("RISK_REGISTER_HAS_NO_RECORDED_RISKS")

    if risk_adjusted_outlook is None:
        missing.append("MONTE_CARLO_OUTLOOK")
    else:
        summary = risk_adjusted_outlook.get("executive_summary") or {}
        p80 = _number(summary.get("p80_contingency"), "risk_adjusted_outlook.p80_contingency")
        if p80 is None:
            missing.append("P80_CONTINGENCY")
        elif p80 > 0:
            signals.append({"code": "P80_CONTINGENCY_ESTIMATE_AVAILABLE", "severity": "INFO", "value": p80, "currency": risk_adjusted_outlook.get("currency")})
            recommendations.append("Bandingkan P80 contingency dengan approved contingency dan governance reserve; jangan menganggapnya sebagai anggaran yang otomatis disetujui.")

    preferred = None
    if scenario_comparison is None:
        missing.append("RECOVERY_SCENARIO_COMPARISON")
    else:
        rows = scenario_comparison.get("scenarios") or []
        eligible = [row for row in rows if row.get("assessment") not in {"NO_SCHEDULE_BENEFIT"} and row.get("duration_saving_days", 0) > 0]
        if eligible:
            preferred = dict(eligible[0])
            signals.append({"code": "RECOVERY_SCENARIO_CANDIDATE_AVAILABLE", "severity": "INFO", "scenario_id": preferred.get("scenario_id")})
            recommendations.append("Tinjau kandidat skenario recovery terhadap CPM, ketersediaan resource, HSE, mutu, kontrak, dan cash flow sebelum keputusan.")
        else:
            missing.append("NO_RECOVERY_SCENARIO_WITH_SCHEDULE_BENEFIT")

    resource_summary = None
    if resource_recovery is None:
        missing.append("RESOURCE_RECOVERY_ESTIMATE")
    elif resource_recovery.get("status") == "ASSESSED":
        baseline = resource_recovery.get("baseline") or {}
        recovery = resource_recovery.get("recovery") or {}
        resource_summary = {
            "baseline_duration_working_days": baseline.get("duration_working_days"),
            "recovery_duration_working_days": recovery.get("duration_working_days"),
            "days_saved": recovery.get("days_saved"),
            "incremental_cost": recovery.get("incremental_cost_vs_baseline"),
            "currency": resource_recovery.get("currency"),
        }
        if recovery.get("days_saved", 0) > 0:
            signals.append({"code": "RESOURCE_RECOVERY_ESTIMATE_AVAILABLE", "severity": "INFO", **resource_summary})
            recommendations.append("Validasi produktivitas tambahan, workface, mobilisasi, biaya, dan keselamatan sebelum menugaskan manpower/equipment tambahan.")

    if not recommendations:
        recommendations.append("Lengkapi data proyek dan lanjutkan monitoring; belum ada dasar yang cukup untuk merekomendasikan intervensi.")

    severity_order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    signals.sort(key=lambda row: (severity_order.get(row["severity"], 3), row["code"]))
    assessed_count = sum(value is not None for value in inputs.values())
    status = "ASSESSED" if assessed_count == len(inputs) and not missing else "PARTIALLY_ASSESSED" if assessed_count else "INSUFFICIENT_DATA"

    return {
        "status": status,
        "decision_authority": "PROJECT_MANAGER / PROJECT_DIRECTOR",
        "signal_count": len(signals),
        "signals": signals,
        "recommendations": list(dict.fromkeys(recommendations)),
        "recovery_scenario_candidate": preferred,
        "resource_recovery_summary": resource_summary,
        "missing_inputs": sorted(set(missing)),
        "decision_gates": [
            "Verify input scope, reporting cut-off, currency and approved baseline.",
            "Recalculate CPM with working calendars and validate the actual critical path.",
            "Confirm resource availability, productivity, HSE, quality and workface constraints.",
            "Review cost exposure, P80 contingency, funding and approval authority.",
            "Record selected option, accountable owner, trigger, due date and measurable success criteria.",
        ],
        "limitations": [
            "Signals are deterministic review rules, not a machine-learning prediction or probability of project failure.",
            "The first scenario is only a candidate according to the supplied comparator order; it is not an automatically optimal or approved choice.",
            "Cost and schedule Monte Carlo percentiles remain separate marginal distributions unless a correlated joint model is independently implemented.",
            "Resource productivity estimates are work-package calculations and do not recalculate the project critical path.",
            "No causal effect of recovery actions is inferred from KPI movement.",
        ],
    }
