"""Read cost and budget evidence from all locally stored project workspaces."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .project_store import ProjectStore
from .portfolio_cashflow_intelligence import build_portfolio_cashflow_view


def _sum_complete_amounts(rows: list[dict[str, Any]], field: str) -> float | None:
    """Sum a dataset only when every row has a valid, finite non-negative value."""
    if not rows:
        return None
    values = []
    for row in rows:
        raw = row.get(field)
        if raw in (None, "") or isinstance(raw, bool):
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value < 0:
            return None
        values.append(value)
    try:
        total = math.fsum(values)
    except OverflowError:
        return None
    return total if math.isfinite(total) else None


def build_stored_portfolio_cashflow_view(database_path: str | Path) -> dict[str, Any]:
    store = ProjectStore(database_path)
    with store._connect() as db:
        project_ids = [row["project_id"] for row in db.execute(
            "SELECT DISTINCT project_id FROM project_records WHERE dataset='project_master' ORDER BY project_id"
        ).fetchall()]
    records: list[dict[str, Any]] = []
    for project_id in project_ids:
        workspace = store.load_project_workspace(project_id)
        if not workspace["project_master"]:
            continue
        master = workspace["project_master"][0]
        project_currency = str(master.get("currency", "")).strip().upper()

        budget = master.get("BAC")
        if budget in (None, ""):
            budget = _sum_complete_amounts(workspace["boq"], "amount")
        elif isinstance(budget, bool):
            budget = None
        else:
            try:
                budget = float(budget)
            except (TypeError, ValueError):
                budget = None
            if budget is not None and (not math.isfinite(budget) or budget < 0):
                budget = None

        actual_cost = _sum_complete_amounts(workspace["actual_cost"], "actual_cost")
        # Never aggregate records whose explicit currency conflicts with the
        # project currency. Missing currency inherits the project-level unit.
        for row in workspace["actual_cost"]:
            row_currency = str(row.get("currency", "")).strip().upper()
            if row_currency and project_currency and row_currency != project_currency:
                actual_cost = None
                break
        for row in workspace["boq"]:
            row_currency = str(row.get("currency", "")).strip().upper()
            if row_currency and project_currency and row_currency != project_currency:
                budget = None
                break

        records.append({
            "project_id": project_id,
            "project_name": master.get("project_name", ""),
            "currency": project_currency,
            "budget": budget,
            "actual_cost": actual_cost,
        })
    result = build_portfolio_cashflow_view(records)
    result["data_source"] = "Local ProjectStore SQLite workspace"
    return result
