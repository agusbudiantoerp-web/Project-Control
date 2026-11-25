"""Bilingual executive portfolio report built from the deterministic scorecard."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from ai_project_control.portfolio_performance import build_portfolio_scorecard


def build_portfolio_executive_report(
    records: Iterable[dict[str, Any]],
    status_date: date | str,
    language: str = "id",
) -> str:
    """Render a concise portfolio report without inventing missing metrics."""
    en = str(language).lower().startswith("en")
    result = build_portfolio_scorecard(records)
    summary = result["summary"]
    rows = result["projects"]
    title = "EXECUTIVE PORTFOLIO PERFORMANCE REPORT" if en else "LAPORAN EKSEKUTIF KINERJA PORTOFOLIO"
    lines = [
        f"# {title}", "",
        f"**Status date:** {status_date}", "",
        "## Portfolio overview" if en else "## Ringkasan portofolio",
        f"- Projects: {summary['project_count']}",
        f"- Assessed: {summary['assessed_count']}",
        f"- Insufficient data: {summary['insufficient_data_count']}",
        f"- RED projects: {summary['red_count']}",
        f"- AMBER projects: {summary['amber_count']}",
        f"- GREEN projects: {summary['green_count']}",
        "",
        "## Budget at completion by currency" if en else "## Anggaran akhir berdasarkan mata uang",
    ]
    budgets = summary["budget_by_currency"]
    if budgets:
        lines.extend(f"- {currency}: {amount:,.2f}" for currency, amount in budgets.items())
    else:
        lines.append("- Not available (amount or currency missing)." if en else "- Belum tersedia (nilai atau mata uang tidak tersedia).")
    lines.extend(["", "## Project scorecard" if en else "## Scorecard proyek",
                  "| Project | Status | Score | Schedule | Cost | Risk |",
                  "|---|---|---:|---|---|---:|"])
    for row in rows:
        score = "—" if row["performance_score"] is None else f"{row['performance_score']:.2f}"
        risk = "—" if row["risk_score"] is None else f"{row['risk_score']:.2f}"
        name = (row["project_name"] or row["project_id"]).replace("|", "\\|")
        lines.append(f"| {name} | {row['status']} | {score} | {row['schedule_state']} | {row['cost_state']} | {risk} |")
    lines.extend(["", "## Management interpretation" if en else "## Interpretasi manajemen"])
    if summary["insufficient_data_count"]:
        lines.append("- Validate missing SPI/CPI inputs before comparing or ranking every project." if en else "- Validasi data SPI/CPI yang belum tersedia sebelum membandingkan atau mengurutkan seluruh proyek.")
    if summary["red_count"]:
        lines.append("- Prioritize review of projects with RED schedule or cost indicators; confirm critical-path and cost evidence." if en else "- Prioritaskan peninjauan proyek dengan indikator jadwal atau biaya RED; konfirmasi bukti jalur kritis dan biaya.")
    if summary["amber_count"]:
        lines.append("- Set recovery triggers and monitor trend movement for AMBER projects." if en else "- Tetapkan pemicu pemulihan dan pantau perubahan tren proyek AMBER.")
    if not summary["red_count"] and not summary["amber_count"]:
        lines.append("- No RED/AMBER status is indicated by the assessed SPI/CPI values; this does not replace risk and data-quality reviews." if en else "- Tidak ada status RED/AMBER dari nilai SPI/CPI yang dinilai; hal ini tidak menggantikan peninjauan risiko dan kualitas data.")
    lines.extend(["", "## Method and limitations" if en else "## Metode dan keterbatasan",
                  f"- {result['scoring_method']}",
                  "- Missing core metrics are marked INSUFFICIENT_DATA, not treated as GREEN." if en else "- Metrik inti yang hilang ditandai INSUFFICIENT_DATA, bukan dianggap GREEN.",
                  "- Budget totals are separated by currency; no FX conversion is assumed." if en else "- Total anggaran dipisahkan berdasarkan mata uang; tidak ada asumsi konversi kurs.",
                  "- This report is a deterministic decision-support summary and requires management validation." if en else "- Laporan ini merupakan ringkasan pendukung keputusan deterministik dan memerlukan validasi manajemen."])
    return "\n".join(lines) + "\n"
