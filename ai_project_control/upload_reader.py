"""Read CSV/XLSX uploads into previewable rows without persisting them.

Designed for Streamlit UploadedFile objects (read() + name) and BytesIO.
Excel formulas are read as cached values only; formula cells without cached
results may appear blank. No macros are executed.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from .import_mapping import map_import_rows, suggest_column_mapping

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 200



def _validate_headers(headers: list[str]) -> None:
    """Normalize and reject blank, duplicate or excessive column headers."""
    if not headers or not any(str(header).strip() for header in headers):
        raise ValueError("No usable header row was found.")
    if len(headers) > MAX_COLUMNS:
        raise ValueError(f"File exceeds the {MAX_COLUMNS} column limit.")
    normalized = [str(header).strip() for header in headers]
    if any(not header for header in normalized):
        raise ValueError("Blank column headers are not allowed.")
    folded = [header.casefold() for header in normalized]
    duplicates = sorted({header for header in folded if folded.count(header) > 1})
    if duplicates:
        raise ValueError("Duplicate column headers: " + ", ".join(duplicates))
    headers[:] = normalized


def read_tabular_upload(uploaded_file: Any, *, sheet_name: str | None = None) -> dict[str, Any]:
    """Read a bounded CSV/XLSX upload and return headers, rows and metadata."""
    filename = str(getattr(uploaded_file, "name", "") or "")
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {"csv", "xlsx"}:
        raise ValueError("Only .csv and .xlsx files are supported; .xls is not supported.")
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    try:
        raw = uploaded_file.read()
    finally:
        # Keep the upload reusable for preview, mapping and persistence reruns.
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("Uploaded file must provide bytes from read().")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
    if not raw:
        raise ValueError("Uploaded file is empty.")

    if extension == "csv":
        try:
            text = bytes(raw).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV must use UTF-8 or UTF-8 with BOM encoding.") from exc
        sample = text[:8192]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        headers = list(reader.fieldnames or [])
        _validate_headers(headers)
        reader.fieldnames = headers
        rows = []
        for index, row in enumerate(reader):
            if index >= MAX_ROWS:
                raise ValueError(f"CSV exceeds the {MAX_ROWS} data-row limit.")
            if None in row:
                raise ValueError(f"CSV row {index + 2} contains more values than the header.")
            rows.append({str(k): v for k, v in row.items()})
        selected_sheet = None
    else:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Reading .xlsx requires openpyxl. Install it before importing Excel files.") from exc
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        try:
            available = workbook.sheetnames
            if not available:
                raise ValueError("Workbook contains no worksheets.")
            chosen = sheet_name or available[0]
            if chosen not in available:
                raise ValueError(f"Worksheet '{chosen}' not found. Available: {', '.join(available)}")
            sheet = workbook[chosen]
            iterator = sheet.iter_rows(values_only=True)
            first = next(iterator, None)
            header_values = list(first or ())
            # Worksheet dimensions may be extended by a later row. Ignore
            # only trailing empty header cells so surplus data cells can be
            # detected against the actual declared header width below.
            while header_values and header_values[-1] in (None, ""):
                header_values.pop()
            headers = [str(value).strip() if value is not None else "" for value in header_values]
            _validate_headers(headers)
            rows = []
            for index, values in enumerate(iterator):
                if index >= MAX_ROWS:
                    raise ValueError(f"Worksheet exceeds the {MAX_ROWS} data-row limit.")
                if len(values) > len(headers) and any(
                    value not in (None, "") for value in values[len(headers):]
                ):
                    raise ValueError(
                        f"Worksheet row {index + 2} contains values beyond the header columns."
                    )
                if not any(value not in (None, "") for value in values):
                    continue
                rows.append({headers[col]: values[col] for col in range(min(len(headers), len(values))) if headers[col]})
            selected_sheet = chosen
        finally:
            workbook.close()

    return {
        "filename": filename,
        "extension": extension,
        "sheet_name": selected_sheet,
        "available_sheets": available if extension == "xlsx" else [],
        "columns": headers,
        "rows": rows,
        "row_count": len(rows),
        "preview": rows[:20],
    }


def prepare_upload_for_table(
    uploaded_file: Any,
    table: str,
    *,
    mapping: dict[str, str] | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    """Read upload, suggest mappings, and optionally map/validate the rows."""
    parsed = read_tabular_upload(uploaded_file, sheet_name=sheet_name)
    suggestion = suggest_column_mapping(table, parsed["columns"])
    chosen_mapping = mapping if mapping is not None else suggestion["mapping"]
    mapped = None
    if chosen_mapping and not suggestion["ambiguous"] and not suggestion["missing_required"]:
        mapped = map_import_rows(table, parsed["rows"], chosen_mapping)
    return {
        "file": {key: value for key, value in parsed.items() if key not in {"rows", "preview"}},
        "suggestion": suggestion,
        "mapping_result": mapped,
        "requires_mapping_review": bool(suggestion["ambiguous"] or suggestion["missing_required"]),
        "limitations": [
            "This operation previews and validates data only; it does not persist or merge records.",
            "For XLSX, the first worksheet is selected unless sheet_name is provided.",
            "Excel formulas are not recalculated; cached cell values are used.",
        ],
    }
