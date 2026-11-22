"""Bilingual deterministic executive summary for project controls."""
from __future__ import annotations
import math


def _num(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def build_executive_summary(project_id, project_name, status_date, metrics, report_errors=None, language="id"):
    en=str(language).lower().startswith("en")
    title="EXECUTIVE PROJECT CONTROL REPORT" if en else "LAPORAN EKSEKUTIF PENGENDALIAN PROYEK"
    lines=[f"# {title}","",f"**Project:** {project_name} ({project_id})",f"**Status date:** {status_date}","","## Executive overview" if en else "## Ringkasan eksekutif"]
    spi=_num(metrics.get("SPI")); cpi=_num(metrics.get("CPI"))
    for key,label_id,label_en in [("BAC","Anggaran total (BAC)","Budget at completion (BAC)"),("EAC","Estimasi biaya akhir (EAC)","Estimate at completion (EAC)")]:
        value=_num(metrics.get(key))
        if value is not None: lines.append(f"- {label_en if en else label_id}: {value:,.2f}.")
    if spi is not None:
        state=("ahead of plan" if spi>1.02 else "behind plan" if spi<0.98 else "approximately on plan") if en else ("lebih cepat dari rencana" if spi>1.02 else "tertinggal dari rencana" if spi<0.98 else "relatif sesuai rencana")
        lines.append(f"- {'Schedule performance' if en else 'Kinerja jadwal'}: SPI {spi:.3f} ({state}).")
    else: lines.append("- Schedule performance unavailable." if en else "- Kinerja jadwal belum tersedia.")
    if cpi is not None:
        state=("cost efficient" if cpi>1.02 else "cost inefficient" if cpi<0.98 else "approximately on budget") if en else ("efisien" if cpi>1.02 else "kurang efisien" if cpi<0.98 else "relatif sesuai anggaran")
        lines.append(f"- {'Cost performance' if en else 'Kinerja biaya'}: CPI {cpi:.3f} ({state}).")
    else: lines.append("- Cost performance unavailable." if en else "- Kinerja biaya belum tersedia.")
    for key,label_id,label_en in [
        ("Integrated forecast finish","Proyeksi tanggal selesai","Integrated forecast finish"),
        ("Risk-adjusted finish P80","Tanggal selesai dengan risiko P80","Risk-adjusted finish P80"),
        ("Critical activities (integrated)","Jumlah aktivitas kritis","Critical activities"),
        ("Risk cost P80","Eksposur biaya risiko P80","Risk cost exposure P80"),
    ]:
        value=metrics.get(key)
        if value is not None: lines.append(f"- {label_en if en else label_id}: {value}.")
    lines.extend(["","## Management attention" if en else "## Perhatian manajemen"])
    attention=[]
    if spi is not None and spi<1: attention.append("Review critical/near-critical work, remaining durations and recovery options." if en else "Tinjau aktivitas kritis/near-critical, sisa durasi, dan opsi pemulihan.")
    if cpi is not None and cpi<1: attention.append("Reconcile actual cost, commitments, quantities and approved changes." if en else "Rekonsiliasi biaya aktual, komitmen, kuantitas, dan perubahan yang disetujui.")
    if not attention: attention.append("No adverse signal is confirmed by available metrics; verify data completeness." if en else "Belum ada sinyal negatif yang dapat dipastikan; verifikasi kelengkapan data.")
    lines.extend("- "+x for x in attention)
    lines.extend(["","## Data quality and limitations" if en else "## Kualitas data dan keterbatasan"])
    errors=report_errors or []
    lines.extend("- "+str(e) for e in errors) if errors else lines.append("- No calculation errors recorded in completed report sections." if en else "- Tidak ada kesalahan perhitungan pada bagian laporan yang berhasil dijalankan.")
    lines.append("- Deterministic summary; it does not establish causal findings or replace management approval." if en else "- Ringkasan deterministik; tidak menetapkan akar masalah dan tidak menggantikan persetujuan manajemen.")
    lines.append("- Forecasts depend on source data, approved assumptions and reporting cut-off." if en else "- Proyeksi bergantung pada data sumber, asumsi yang disetujui, dan cut-off pelaporan.")
    return "\n".join(lines)+"\n"
