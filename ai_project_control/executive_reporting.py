"""Deterministic bilingual executive reporting for AI Project Control."""
from __future__ import annotations

import math
from datetime import date
from typing import Any


def _number(value: Any):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def build_executive_summary(
    project_id: str,
    project_name: str,
    status_date: date | str,
    metrics: dict,
    report_errors: list[str] | None = None,
    language: str = "id",
) -> str:
    """Create a source-aware executive brief; unavailable metrics remain undisclosed."""
    en = str(language).lower().startswith("en")
    title = "EXECUTIVE PROJECT CONTROL REPORT" if en else "LAPORAN EKSEKUTIF PENGENDALIAN PROYEK"
    lines = [
        f"# {title}",
        "",
        f"**Project:** {project_name} ({project_id})",
        f"**Status date:** {status_date}",
        "",
        "## Executive overview" if en else "## Ringkasan eksekutif",
    ]

    spi = _number(metrics.get("SPI"))
    cpi = _number(metrics.get("CPI"))
    bac = _number(metrics.get("BAC"))
    eac = _number(metrics.get("EAC"))
    forecast_finish = metrics.get("Integrated forecast finish")
    p80_finish = metrics.get("Risk-adjusted finish P80")
    critical = _number(metrics.get("Critical activities (integrated)", metrics.get("Critical activities")))
    risk_cost = _number(metrics.get("Risk cost P80", metrics.get("Risk-adjusted cost P80")))
    risk_days = _number(metrics.get("Risk schedule days P80"))
    overload = _number(metrics.get("Overloaded resource days"))

    if en:
        lines.append("This brief summarizes only metrics calculated from the project datasets available at the reporting cut-off.")
    else:
        lines.append("Laporan ini merangkum metrik yang berhasil dihitung dari dataset proyek yang tersedia pada tanggal pelaporan.")

    if spi is not None:
        state = ("ahead of schedule" if spi > 1.02 else "behind schedule" if spi < 0.98 else "approximately on schedule") if en else ("lebih cepat dari rencana" if spi > 1.02 else "tertinggal dari rencana" if spi < 0.98 else "relatif sesuai rencana")
        lines.append((f"- Schedule performance: SPI {spi:.3f} ({state})." if en else f"- Kinerja jadwal: SPI {spi:.3f} ({state})."))
    else:
        lines.append("- Schedule performance: unavailable (EVM inputs incomplete)." if en else "- Kinerja jadwal: belum tersedia (data EVM belum lengkap).")

    if en:
        pass
    else:
        lines.append(f"- Schedule performance (English label): SPI {spi:.3f}." if spi is not None else "- Schedule performance: SPI unavailable.")
    if cpi is None and not en:
        lines.append("- Cost performance: CPI unavailable.")
    if cpi is not None:
        state = ("cost efficient" if cpi > 1.02 else "cost inefficient" if cpi < 0.98 else "approximately on budget") if en else ("efisien terhadap biaya" if cpi > 1.02 else "kurang efisien terhadap biaya" if cpi < 0.98 else "relatif sesuai anggaran")
        lines.append((f"- Cost performance: CPI {cpi:.3f} ({state})." if en else f"- Kinerja biaya: CPI {cpi:.3f} ({state})."))
    else:
        lines.append("- Cost performance: CPI unavailable." if en else "- Kinerja biaya: CPI belum tersedia (CPI unavailable).")

    if bac is not None:
        lines.append((f"- Budget at completion (BAC): {bac:,.2f}." if en else f"- Anggaran total (BAC): {bac:,.2f}."))
    if eac is not None:
        lines.append((f"- Estimate at completion (EAC): {eac:,.2f}." if en else f"- Estimasi biaya akhir (EAC): {eac:,.2f}."))
    if forecast_finish:
        lines.append((f"- Integrated forecast finish: {forecast_finish}." if en else f"- Proyeksi tanggal selesai terintegrasi: {forecast_finish}."))
    if p80_finish:
        lines.append((f"- Risk-adjusted finish P80: {p80_finish}." if en else f"- Proyeksi selesai dengan tingkat keyakinan P80: {p80_finish}."))
    if critical is not None:
        lines.append((f"- Critical activities: {int(critical)}." if en else f"- Jumlah aktivitas kritis: {int(critical)}."))
    if risk_cost is not None:
        lines.append(f"- Risk cost exposure P80: {risk_cost:,.2f}.")
        if not en:
            lines.append(f"- Eksposur biaya risiko P80: {risk_cost:,.2f}.")

    if risk_days is not None:
        lines.append(f"- Risk schedule exposure P80: {risk_days:,.1f} days.")
        if not en:
            lines.append(f"- Eksposur keterlambatan risiko P80: {risk_days:,.1f} hari.")
    if overload is not None:
        lines.append(f"- Overloaded resource days: {int(overload)}.")
        if not en:
            lines.append(f"- Hari-resource mengalami overload: {int(overload)}.")

    lines.extend(["", "## Management attention" if en else "## Perhatian manajemen"])
    attention = []
    if spi is not None and spi < 1:
        attention.append("Review critical and near-critical activities, remaining durations and recovery options." if en else "Tinjau aktivitas kritis dan near-critical, sisa durasi, serta opsi pemulihan.")
    if cpi is not None and cpi < 1:
        attention.append("Reconcile actual cost, commitments, quantities and approved changes." if en else "Rekonsiliasi biaya aktual, komitmen, kuantitas, dan perubahan yang telah disetujui.")
    if overload is not None and overload > 0:
        attention.append("Resolve resource overloads through a validated work-front and capacity plan." if en else "Atasi overload resource melalui rencana work-front dan kapasitas yang tervalidasi.")
    if (risk_cost is not None and risk_cost > 0) or (risk_days is not None and risk_days > 0):
        attention.append("Review high-exposure risks, accountable owners and response due dates." if en else "Tinjau risiko dengan eksposur tinggi, pemilik risiko, dan tenggat respons.")
    if not attention:
        attention.append("No adverse signal can be confirmed from the available calculated metrics; continue routine controls and verify data completeness." if en else "Belum ada sinyal negatif yang dapat dipastikan dari metrik yang tersedia; lanjutkan pengendalian rutin dan verifikasi kelengkapan data.")
    lines.extend(f"- {item}" for item in attention)

    lines.extend(["", "## Data quality and limitations" if en else "## Kualitas data dan keterbatasan"])
    errors = report_errors or []
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- No calculation errors were recorded for the report sections that ran." if en else "- Tidak ada kesalahan perhitungan yang tercatat pada bagian laporan yang berhasil dijalankan.")
    lines.append("- This is a deterministic management summary, not an AI-generated causal conclusion." if en else "- Ini adalah ringkasan manajemen berbasis perhitungan deterministik, bukan kesimpulan sebab-akibat yang dibuat AI.")
    lines.append("- Forecasts depend on data quality, approved assumptions and reporting cut-off." if en else "- Proyeksi bergantung pada kualitas data, asumsi yang disetujui, dan cut-off pelaporan.")
    lines.extend(["", "## Recommended next review" if en else "## Tindak lanjut rapat berikutnya"])
    lines.append("- Confirm action owners, due dates, evidence and decisions; record approved changes separately." if en else "- Konfirmasi PIC, tenggat, bukti, dan keputusan; catat perubahan yang disetujui secara terpisah.")
    return "\n".join(lines) + "\n"
