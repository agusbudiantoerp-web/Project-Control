"""Safe, schema-light column mapping for project-control CSV/Excel imports.

This module accepts rows already parsed by a CSV/XLSX reader. It does not read
files, execute formulas, or silently choose between ambiguous source columns.
"""
from __future__ import annotations

import re
from typing import Any

from .data_quality_validation import TABLE_KEYS, validate_project_control_data

ALIASES = {
    "project_master": {
        "project_id": ("project id", "project code", "kode proyek", "id proyek"),
        "project_name": ("project name", "nama proyek"),
        "currency": ("currency", "mata uang"),
        "bac": ("bac", "budget at completion", "anggaran awal"),
    },
    "wbs": {
        "project_id": ("project id", "project code", "kode proyek"),
        "wbs_id": ("wbs id", "wbs code", "kode wbs"),
        "parent_wbs_id": ("parent wbs", "parent wbs id"),
        "description": ("description", "uraian"),
    },
    "boq": {
        "project_id": ("project id", "project code", "kode proyek"),
        "boq_id": ("boq id", "item code", "kode item"),
        "quantity": ("quantity", "qty", "volume"),
        "unit_rate": ("unit rate", "unit price", "harga satuan"),
        "amount": ("amount", "total", "nilai"),
    },
    "activities": {
        "project_id": ("project id", "project code", "kode proyek"),
        "activity_id": ("activity id", "activity code", "kode aktivitas"),
        "duration_days": ("duration", "duration days", "durasi"),
        "planned_duration_days": ("planned duration", "durasi rencana"),
        "actual_duration_days": ("actual duration", "durasi aktual"),
    },
    "progress": {
        "project_id": ("project id", "project code", "kode proyek"),
        "activity_id": ("activity id", "activity code", "kode aktivitas"),
        "period": ("period", "month", "periode", "bulan"),
        "planned_value": ("planned value", "pv"),
        "earned_value": ("earned value", "ev"),
        "physical_progress_pct": ("physical progress", "progress pct", "progress %", "progres fisik"),
    },
    "actual_cost": {
        "project_id": ("project id", "project code", "kode proyek"),
        "period": ("period", "month", "periode", "bulan"),
        "cost_code": ("cost code", "kode biaya"),
        "actual_cost": ("actual cost", "ac", "biaya aktual"),
    },
    "risk": {
        "project_id": ("project id", "project code", "kode proyek"),
        "risk_id": ("risk id", "risk code", "kode risiko"),
        "probability": ("probability", "probabilitas"),
        "impact": ("impact", "dampak"),
        "exposure": ("exposure", "paparan risiko"),
    },
    "resources": {
        "resource_type": ("resource type", "jenis resource", "jenis sumber daya", "category"),
        "resource_name": ("resource name", "nama resource", "nama sumber daya"),
        "unit": ("unit", "satuan", "uom"),
        "project_id": ("project id", "project code", "kode proyek"),
        "resource_id": ("resource id", "resource code", "kode resource"),
        "period": ("period", "month", "periode", "bulan"),
        "planned_units": ("planned units", "kebutuhan rencana"),
        "actual_units": ("actual units", "realisasi resource"),
        "capacity_units": ("capacity", "capacity units", "kapasitas"),
    },
}


def _normalise_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text)


def suggest_column_mapping(table: str, source_columns: list[str]) -> dict[str, Any]:
    """Suggest only unique exact/alias matches; report ambiguous candidates."""
    if table not in TABLE_KEYS:
        raise ValueError(f"Unsupported table: {table}")
    normalized_sources: dict[str, list[str]] = {}
    for source in source_columns:
        normalized_sources.setdefault(_normalise_header(source), []).append(source)

    mapping: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}
    for target, aliases in ALIASES.get(table, {}).items():
        accepted = {_normalise_header(target), *(_normalise_header(a) for a in aliases)}
        matches = [original for norm, originals in normalized_sources.items()
                   if norm in accepted for original in originals]
        if len(matches) == 1:
            mapping[target] = matches[0]
        elif len(matches) > 1:
            ambiguous[target] = matches

    missing_required = [field for field in TABLE_KEYS[table] if field not in mapping]
    return {
        "table": table,
        "mapping": mapping,
        "ambiguous": ambiguous,
        "missing_required": missing_required,
        "ready": not ambiguous and not missing_required,
    }


def map_import_rows(
    table: str,
    source_rows: list[dict[str, Any]],
    mapping: dict[str, str],
    *,
    validate: bool = True,
) -> dict[str, Any]:
    """Map source dictionaries into canonical fields and optionally validate."""
    if table not in TABLE_KEYS:
        raise ValueError(f"Unsupported table: {table}")
    if not isinstance(source_rows, list) or any(not isinstance(row, dict) for row in source_rows):
        raise TypeError("source_rows must be a list of dictionaries")
    if not isinstance(mapping, dict):
        raise TypeError("mapping must be a dictionary of target_field to source_column")

    allowed_targets = set(ALIASES.get(table, {})) | set(TABLE_KEYS[table])
    unknown_targets = sorted(set(mapping) - allowed_targets)
    if unknown_targets:
        raise ValueError(f"Unknown target fields for {table}: {', '.join(unknown_targets)}")

    mapped = []
    for row in source_rows:
        output = {}
        for target, source in mapping.items():
            if source in row:
                output[target] = row[source]
        mapped.append(output)

    validation = None
    if validate:
        validation = validate_project_control_data({table: mapped})
    return {
        "table": table,
        "rows": mapped,
        "row_count": len(mapped),
        "validation": validation,
        "ready_for_analysis": bool(validation and validation["status"] == "VALID"),
        "limitations": [
            "Source rows must be parsed by a trusted CSV/XLSX reader before mapping.",
            "No records are persisted or merged into a live project database.",
            "Column suggestions are conservative; ambiguous columns require manual selection.",
        ],
    }
