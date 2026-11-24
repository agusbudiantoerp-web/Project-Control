"""Read cost and budget evidence from all locally stored project workspaces."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_store import ProjectStore
from .portfolio_cashflow_intelligence import build_portfolio_cashflow_view


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
        budget = master.get("BAC")
        if budget in (None, ""):
            try:
                budget = sum(float(row.get("amount") or 0) for row in workspace["boq"])
            except (TypeError, ValueError):
                budget = None
        try:
            actual_cost = sum(float(row.get("actual_cost") or 0) for row in workspace["actual_cost"])
        except (TypeError, ValueError):
            actual_cost = None
        records.append({
            "project_id": project_id,
            "project_name": master.get("project_name", ""),
            "currency": master.get("currency", ""),
            "budget": budget,
            "actual_cost": actual_cost,
        })
    result = build_portfolio_cashflow_view(records)
    result["data_source"] = "Local ProjectStore SQLite workspace"
    return result
