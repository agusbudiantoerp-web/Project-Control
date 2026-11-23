"""Integrated bilingual portfolio executive report from explicitly supplied records."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable


def _safe(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "nat"} else "—"


def build_integrated_executive_report(
    *,
    portfolio_records: Iterable[dict[str, Any]],
    status_date: Any,
    director_decisions: dict[str, Any] | None = None,
    action_register: dict[str, Any] | None = None,
    health_monitoring: dict[str, Any] | None = None,
    recovery_assessment: dict[str, Any] | None = None,
    scenario_comparison: dict[str, Any] | None = None,
    language: str = "id",
) -> str:
    """Compose an executive report without deriving missing metrics."""
    en = str(language).lower().startswith("en")
    try:
        report_date = status_date.isoformat() if isinstance(status_date, date) else date.fromisoformat(str(status_date)).isoformat()
    except (TypeError, ValueError):
        raise ValueError("status_date must be a valid ISO date") from None
    projects = [dict(row) for row in portfolio_records]
    lines = [
        "# " + ("INTEGRATED PORTFOLIO EXECUTIVE REPORT" if en else "LAPORAN EKSEKUTIF PORTOFOLIO TERINTEGRASI"),
        "",
        f"**" + ("Reporting date" if en else "Tanggal laporan") + f":** {report_date}",
        f"**" + ("Projects in supplied portfolio" if en else "Jumlah proyek dalam data portfolio") + f":** {len(projects)}",
        "",
        "## " + ("Portfolio register" if en else "Register portfolio"),
        "",
        "| Project ID | Project | SPI | CPI | Status |",
        "|---|---|---:|---:|---|",
    ]
    for row in projects:
        lines.append("| " + " | ".join(_safe(row.get(key)) for key in
            ("project_id", "project_name", "SPI", "CPI", "portfolio_status")) + " |")
    if not projects:
        lines.append("| — | " + ("No project records supplied" if en else "Tidak ada data proyek") + " | — | — | — |")

    lines.extend(["", "## " + ("Director decision matrix" if en else "Matriks keputusan direktur")])
    decisions = (director_decisions or {}).get("decisions", [])
    decision_summary = (director_decisions or {}).get("summary", {})
    if decisions:
        for key, label in (("p1_count", "P1"), ("p2_count", "P2"), ("data_review_count", "DATA_REVIEW"), ("unassessed_count", "UNASSESSED")):
            if key in decision_summary:
                lines.append(f"- {label}: {decision_summary[key]}")
        lines.extend(["", "| Project | Priority | Evidence points | Recommended action |", "|---|---|---:|---|"])
        for row in decisions:
            lines.append("| " + " | ".join(_safe(row.get(k)) for k in
                ("project_name", "priority", "evidence_points", "recommended_action")) + " |")
    else:
        lines.append("- " + ("Decision matrix data not supplied." if en else "Data matriks keputusan belum tersedia."))

    lines.extend(["", "## " + ("Corrective action register" if en else "Register tindakan korektif")])
    actions = (action_register or {}).get("actions", [])
    action_summary = (action_register or {}).get("summary", {})
    if actions:
        for key, label in (("open_count", "OPEN"), ("in_progress_count", "IN_PROGRESS"), ("blocked_count", "BLOCKED"), ("completed_count", "COMPLETED"), ("overdue_count", "OVERDUE")):
            if key in action_summary:
                lines.append(f"- {label}: {action_summary[key]}")
        lines.extend(["", "| Action | Project | Owner | Due date | Priority | Status |", "|---|---|---|---|---|---|"])
        for row in actions:
            lines.append("| " + " | ".join(_safe(row.get(k)) for k in
                ("title", "project_id", "owner", "due_date", "priority", "status")) + " |")
    else:
        lines.append("- " + ("No action records supplied." if en else "Belum ada data tindakan yang diberikan."))

    lines.extend(["", "## " + ("Portfolio health trends" if en else "Tren kesehatan portfolio")])
    health_rows = (health_monitoring or {}).get("projects", [])
    if health_rows:
        lines.extend(["| Project | Status | Baseline date | Latest date | SPI change | CPI change | Risk change |", "|---|---|---|---|---:|---:|---:|"])
        for row in health_rows:
            changes = row.get("changes") or {}
            vals = [row.get("project_id"), row.get("status"), row.get("baseline_date"), row.get("latest_date"),
                    changes.get("SPI"), changes.get("CPI"), changes.get("risk_score")]
            lines.append("| " + " | ".join(_safe(v) for v in vals) + " |")
    else:
        lines.append("- " + ("No dated trend snapshots supplied." if en else "Belum ada snapshot tren bertanggal."))

    lines.extend(["", "## " + ("Recovery assessment" if en else "Penilaian pemulihan")])
    if recovery_assessment:
        for key in ("status", "baseline_variance_days", "recovery_target_gap_days", "spi_gap", "funding_gap"):
            if key in recovery_assessment:
                lines.append(f"- {key}: {_safe(recovery_assessment.get(key))}")
        for signal in recovery_assessment.get("signals", []):
            lines.append("- " + _safe(signal))
    else:
        lines.append("- " + ("No recovery assessment supplied." if en else "Belum ada assessment pemulihan."))

    lines.extend(["", "## " + ("Recovery scenario comparison" if en else "Perbandingan skenario pemulihan")])
    scenario_rows = (scenario_comparison or {}).get("scenarios", [])
    if scenario_rows:
        lines.extend(["| Scenario | Days saved | Remaining days | Incremental cost | Risk score | Assessment |", "|---|---:|---:|---:|---:|---|"])
        for row in scenario_rows:
            lines.append("| " + " | ".join(_safe(row.get(k)) for k in
                ("name", "duration_saving_days", "remaining_duration_days", "incremental_cost", "risk_score", "assessment")) + " |")
    else:
        lines.append("- " + ("No recovery scenarios supplied." if en else "Belum ada skenario pemulihan."))

    lines.extend(["", "## " + ("Governance and limitations" if en else "Tata kelola dan keterbatasan")])
    limitations = [
        "Report includes only supplied and available records; missing values are not inferred.",
        "Portfolio data may represent a local workspace only, not an enterprise-wide consolidated database.",
        "Priority and recovery comparisons are screening aids; approvals require authorized project, finance, engineering, safety and contract review.",
        "Financial values in different currencies must not be summed without an approved conversion basis.",
    ]
    if not projects:
        limitations.append("No portfolio projects were supplied for this report.")
    lines.extend("- " + item for item in limitations)
    return "\n".join(lines) + "\n"
