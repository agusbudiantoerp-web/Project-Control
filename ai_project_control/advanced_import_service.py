"""Advanced source intake for Primavera P6 XER and drawing-to-BOQ review.

All imported records are routed into the primary ProjectStore workspace. XER
schedule durations are converted from P6 hours to nominal 8-hour days; calendar
semantics remain a separate professional review responsibility.
"""
from __future__ import annotations

import base64
import json
import math
import re
from typing import Any

import requests

from .project_store import ProjectStore
from .schedule_engine import calculate_critical_path

MAX_XER_BYTES = 30 * 1024 * 1024
MAX_DRAWING_IMAGE_BYTES = 12 * 1024 * 1024
MAX_DRAWING_TAKEOFF_ITEMS = 500
MAX_GEMINI_RESPONSE_CHARS = 1_000_000


def parse_xer_tables(raw: bytes) -> dict[str, list[dict[str, str]]]:
    """Parse the tab-delimited %T/%F/%R tables from a Primavera P6 XER file."""
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("XER upload must be bytes")
    if not raw:
        raise ValueError("XER file is empty")
    if len(raw) > MAX_XER_BYTES:
        raise ValueError("XER file exceeds the 30 MB import limit")
    text = bytes(raw).decode("latin-1", errors="replace")
    tables: dict[str, list[dict[str, str]]] = {}
    current: str | None = None
    fields: list[str] = []
    for line in text.splitlines():
        parts = line.rstrip("\r\n").split("\t")
        if not parts:
            continue
        if parts[0] == "%T" and len(parts) > 1:
            current = parts[1].strip()
            if not current:
                raise ValueError("XER contains an empty table name")
            tables.setdefault(current, [])
            fields = []
        elif parts[0] == "%F" and current:
            fields = [value.strip() for value in parts[1:]]
            folded = [field.casefold() for field in fields]
            if not fields or any(not field for field in fields) or len(folded) != len(set(folded)):
                raise ValueError(f"XER table {current} has blank or duplicate field names")
        elif parts[0] == "%R" and current and fields:
            values = parts[1:]
            if len(values) > len(fields) and any(value.strip() for value in values[len(fields):]):
                raise ValueError(f"XER table {current} contains a row wider than its field header")
            if len(values) < len(fields):
                values += [""] * (len(fields) - len(values))
            tables[current].append(dict(zip(fields, values[:len(fields)])))
    if not tables:
        raise ValueError("File does not contain recognizable Primavera XER tables")
    return tables


def list_xer_source_projects(raw: bytes) -> list[dict[str, str]]:
    """Return P6 source projects so multi-project XER files can be scoped safely."""
    tables = parse_xer_tables(raw)
    projects = tables.get("PROJECT", [])
    output = []
    seen = set()
    for row in projects:
        source_id = str(row.get("proj_id", "")).strip()
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        output.append({
            "source_project_id": source_id,
            "project_name": str(row.get("proj_name") or row.get("proj_short_name") or source_id).strip(),
            "project_code": str(row.get("proj_short_name", "")).strip(),
        })
    if output:
        return output
    task_ids = sorted({
        str(row.get("proj_id", "")).strip()
        for row in tables.get("TASK", [])
        if str(row.get("proj_id", "")).strip()
    })
    return [
        {"source_project_id": value, "project_name": value, "project_code": value}
        for value in task_ids
    ]


def _first_date(*values: Any) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text and text.lower() not in {"nan", "nat", "none"}:
            candidate = text[:10]
            return candidate
    return None


def prepare_xer_workspace_import(
    raw: bytes,
    *,
    project_id: str,
    project_name: str,
    currency: str,
    source_project_id: str | None = None,
) -> dict[str, Any]:
    """Convert one selected P6 project into primary workspace dataset records."""
    target_id = str(project_id).strip()
    target_name = str(project_name).strip()
    project_currency = str(currency).strip().upper()
    if not target_id or not target_name or not project_currency:
        raise ValueError("Target Project ID, project name and currency are required")
    if len(project_currency) != 3 or not project_currency.isalpha():
        raise ValueError("Project currency must be a three-letter ISO currency code")

    tables = parse_xer_tables(raw)
    task_rows = tables.get("TASK", [])
    if not task_rows:
        raise ValueError("XER does not contain TASK activity records")
    available = list_xer_source_projects(raw)
    source_ids = sorted({
        str(row.get("proj_id", "")).strip()
        for row in task_rows
        if str(row.get("proj_id", "")).strip()
    })
    if source_project_id and source_ids:
        selected_source = str(source_project_id).strip()
        if selected_source not in source_ids:
            raise ValueError("Selected P6 source project does not match the TASK records")
    elif source_project_id and not source_ids:
        if len(available) > 1:
            raise ValueError(
                "XER has multiple PROJECT records but TASK rows omit proj_id; "
                "the source project cannot be safely isolated."
            )
        selected_source = ""
    elif len(source_ids) > 1 or (not source_ids and len(available) > 1):
        raise ValueError("XER contains multiple projects; select one P6 source project before importing")
    else:
        selected_source = source_ids[0] if source_ids else ""

    selected_tasks = [
        row for row in task_rows
        if not selected_source or str(row.get("proj_id", "")).strip() == selected_source
    ]
    if not selected_tasks:
        raise ValueError("Selected P6 source project contains no TASK records")
    task_id_values = [str(row.get("task_id", "")).strip() for row in selected_tasks]
    if any(not value for value in task_id_values) or len(task_id_values) != len(set(task_id_values)):
        raise ValueError("Selected P6 project contains blank or duplicate task IDs")
    activity_id_values = [
        str(row.get("task_code") or row.get("task_id") or "").strip()
        for row in selected_tasks
    ]
    if any(not value for value in activity_id_values) or len(activity_id_values) != len(set(activity_id_values)):
        raise ValueError("Selected P6 project contains blank or duplicate activity codes")
    task_ids = set(task_id_values)
    code_by_id = dict(zip(task_id_values, activity_id_values))
    predecessor_map: dict[str, list[str]] = {}
    for relation in tables.get("TASKPRED", []):
        successor = str(relation.get("task_id", "")).strip()
        predecessor = str(relation.get("pred_task_id", "")).strip()
        if successor not in task_ids:
            continue
        if predecessor not in task_ids:
            raise ValueError(
                f"P6 activity {successor} references predecessor {predecessor} outside the selected project."
            )
        if code_by_id[predecessor] in predecessor_map.get(successor, []):
            raise ValueError(f"P6 activity {successor} contains a duplicate predecessor link")
        relation_type = str(relation.get("pred_type") or "PR_FS").strip().upper()
        if relation_type not in {"PR_FS", "FS"}:
            raise ValueError(
                f"P6 relationship {predecessor} → {successor} uses unsupported type "
                f"{relation_type}; only Finish-to-Start relationships are imported."
            )
        raw_lag = relation.get("lag_hr_cnt", "0")
        try:
            lag_hours = float(raw_lag or 0)
        except (TypeError, ValueError):
            raise ValueError(
                f"P6 relationship {predecessor} → {successor} has an invalid lag."
            ) from None
        if not math.isfinite(lag_hours) or abs(lag_hours) > 1e-9:
            raise ValueError(
                f"P6 relationship {predecessor} → {successor} has a non-zero lag; "
                "lags are not supported by the workspace CPM engine."
            )
        predecessor_map.setdefault(successor, []).append(code_by_id[predecessor])

    activities = []
    for index, row in enumerate(selected_tasks, 1):
        source_task_id = str(row.get("task_id", "")).strip()
        activity_id = str(row.get("task_code") or source_task_id).strip()
        if not activity_id:
            raise ValueError(f"XER task row {index} has no task_code or task_id")
        raw_hours = row.get("target_drtn_hr_cnt")
        if raw_hours in (None, ""):
            raw_hours = row.get("remain_drtn_hr_cnt")
        try:
            hours = float(raw_hours)
        except (TypeError, ValueError):
            raise ValueError(f"Activity {activity_id} has no valid P6 duration in hours") from None
        if not math.isfinite(hours) or hours < 0:
            raise ValueError(f"Activity {activity_id} has an invalid P6 duration")
        activities.append({
            "project_id": target_id,
            "activity_id": activity_id,
            "activity_name": str(row.get("task_name") or activity_id).strip(),
            "wbs_id": str(row.get("wbs_id", "")).strip(),
            "duration_days": hours / 8.0,
            "planned_start": _first_date(row.get("target_start_date"), row.get("early_start_date")),
            "planned_finish": _first_date(row.get("target_end_date"), row.get("early_end_date")),
            "predecessor_ids": ",".join(predecessor_map.get(source_task_id, [])),
            "source_format": "PRIMAVERA_P6_XER",
            "source_task_id": source_task_id,
        })

    raw_wbs_rows = tables.get("PROJWBS", [])
    if len(available) > 1 and any(not str(row.get("proj_id", "")).strip() for row in raw_wbs_rows):
        raise ValueError(
            "XER has multiple projects but some WBS rows omit proj_id; "
            "WBS records cannot be safely isolated."
        )
    schedule_check = calculate_critical_path(activities)
    if schedule_check.get("status") != "ASSESSED":
        raise ValueError(
            "P6 activity dependency network is not a valid finish-to-start CPM network: "
            + "; ".join(schedule_check.get("issues", []))
        )

    wbs_rows = []
    for row in raw_wbs_rows:
        if selected_source and str(row.get("proj_id", "")).strip() not in {"", selected_source}:
            continue
        wbs_id = str(row.get("wbs_id", "")).strip()
        if not wbs_id:
            continue
        wbs_rows.append({
            "project_id": target_id,
            "wbs_id": wbs_id,
            "parent_wbs_id": str(row.get("parent_wbs_id", "")).strip(),
            "wbs_name": str(row.get("wbs_name") or row.get("wbs_short_name") or wbs_id).strip(),
            "source_format": "PRIMAVERA_P6_XER",
        })

    wbs_ids = {row["wbs_id"] for row in wbs_rows}
    parent_by_wbs = {
        row["wbs_id"]: row["parent_wbs_id"]
        for row in wbs_rows
    }
    for wbs_id, parent_id in parent_by_wbs.items():
        if parent_id in {"", "0"}:
            continue
        if parent_id not in wbs_ids:
            raise ValueError(f"P6 WBS {wbs_id} references missing parent WBS {parent_id}")
        visited = {wbs_id}
        current = parent_id
        while current:
            if current in visited:
                raise ValueError(f"P6 WBS hierarchy contains a cycle at {current}")
            visited.add(current)
            current = parent_by_wbs.get(current, "")
    if wbs_ids:
        missing_wbs = sorted({
            row["wbs_id"] for row in activities
            if row["wbs_id"] and row["wbs_id"] not in wbs_ids
        })
        if missing_wbs:
            raise ValueError("P6 activities reference WBS IDs not included in the selected project: " + ", ".join(missing_wbs[:10]))

    source_project = next(
        (row for row in available if row["source_project_id"] == selected_source),
        {},
    )
    master = {
        "project_id": target_id,
        "project_name": target_name or source_project.get("project_name") or target_id,
        "currency": project_currency,
        "source_format": "PRIMAVERA_P6_XER",
        "source_project_id": selected_source,
    }
    return {
        "project_master": [master],
        "wbs": wbs_rows,
        "activities": activities,
        "source_project_id": selected_source,
        "source_project_name": source_project.get("project_name", ""),
        "source_project_options": available,
        "counts": {"wbs": len(wbs_rows), "activities": len(activities)},
        "limitations": [
            "P6 target duration hours are converted to nominal 8-hour days for the workspace CPM engine.",
            "Calendars, holidays, constraints, resource leveling, relationship types and lags are not recalculated by this import.",
            "Imported P6 dates are source references; validate calendars and baseline meaning before using them for forecasts.",
        ],
    }


def import_xer_to_workspace(
    store: ProjectStore,
    raw: bytes,
    *,
    project_id: str,
    project_name: str,
    currency: str,
    source_project_id: str | None = None,
    mode: str = "upsert",
) -> dict[str, Any]:
    """Atomically save Project Master, WBS and activities from one XER project."""
    prepared = prepare_xer_workspace_import(
        raw, project_id=project_id, project_name=project_name,
        currency=currency, source_project_id=source_project_id,
    )
    existing = store.load_dataset(project_id, "project_master")
    master = dict(existing[0]) if existing else {}
    existing_currency = str(master.get("currency", "")).strip().upper()
    incoming_currency = prepared["project_master"][0]["currency"]
    if existing_currency and existing_currency != incoming_currency:
        raise ValueError(
            f"Project currency is already {existing_currency}; XER import currency "
            f"{incoming_currency} does not match. Use a new Project ID or reconcile currency first."
        )
    master.update(prepared["project_master"][0])
    datasets = {
        "project_master": [master],
        "wbs": prepared["wbs"],
        "activities": prepared["activities"],
    }
    saved = store.save_datasets(project_id, datasets, mode=mode)
    return {**prepared, "saved": saved, "status": "COMMITTED"}


def analyze_drawing_page_with_gemini(
    image_bytes: bytes,
    api_key: str,
    *,
    model: str = "gemini-2.5-flash",
    timeout: float = 120,
) -> list[dict[str, Any]]:
    """Extract an explicitly labelled draft takeoff from one drawing page."""
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ValueError("Drawing page image is empty")
    if len(image_bytes) > MAX_DRAWING_IMAGE_BYTES:
        raise ValueError("Drawing page image exceeds the 12 MB limit")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("GEMINI_API_KEY is required for drawing analysis")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Gemini model name is required")
    model_name = model.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", model_name):
        raise ValueError("Gemini model name contains unsupported characters")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(float(timeout)) or timeout <= 0:
        raise ValueError("timeout must be a finite positive number")

    prompt = (
        "You are a construction quantity surveyor. Inspect this engineering drawing page. "
        "Extract only items whose dimensions, counts, schedules or quantities are explicitly visible. "
        "Do not invent dimensions, scale, thickness, lengths or quantities. If a required dimension is "
        "missing, set quantity to null and explain what must be measured. Return ONLY valid JSON: an "
        "array of objects with keys discipline,item_code,description,unit,quantity,measurement_method,"
        "confidence,assumptions. Use SI units where supported. Confidence must be High, Medium or Low. "
        "Every quantity is a draft and must be checked by a human quantity surveyor."
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    try:
        response = requests.post(
            endpoint,
            headers={"x-goog-api-key": api_key.strip()},
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(bytes(image_bytes)).decode("ascii"),
                        }},
                    ],
                }],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
            },
            timeout=float(timeout),
        )
        response.raise_for_status()
        payload = response.json()
        raw_text = payload["candidates"][0]["content"]["parts"][0]["text"]
        if not isinstance(raw_text, str) or len(raw_text) > MAX_GEMINI_RESPONSE_CHARS:
            raise ValueError("Gemini drawing response exceeds the supported output limit")
        text = raw_text.strip()
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError("Gemini drawing analysis failed; check API configuration and provider response.") from None
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:-1])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini returned unreadable drawing-analysis JSON.") from None
    if not isinstance(data, list):
        raise RuntimeError("Gemini drawing response must be a JSON array")
    if len(data) > MAX_DRAWING_TAKEOFF_ITEMS:
        raise RuntimeError(
            f"Gemini returned more than the {MAX_DRAWING_TAKEOFF_ITEMS} item review limit"
        )
    rows = []
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            continue
        raw_quantity = item.get("quantity")
        quantity = None
        if raw_quantity not in (None, "") and not isinstance(raw_quantity, bool):
            try:
                parsed_quantity = float(raw_quantity)
                if math.isfinite(parsed_quantity) and parsed_quantity >= 0:
                    quantity = parsed_quantity
            except (TypeError, ValueError):
                pass
        confidence = str(item.get("confidence", "Low")).title()
        if confidence not in {"High", "Medium", "Low"}:
            confidence = "Low"
        rows.append({
            "item_code": str(item.get("item_code") or f"TAKEOFF-{index:03d}").strip(),
            "discipline": str(item.get("discipline", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "unit": str(item.get("unit", "")).strip(),
            "quantity": quantity,
            "measurement_method": str(item.get("measurement_method", "")).strip(),
            "confidence": confidence,
            "assumptions": str(item.get("assumptions", "")).strip(),
            "review_status": "PENDING_REVIEW",
        })
    return rows
