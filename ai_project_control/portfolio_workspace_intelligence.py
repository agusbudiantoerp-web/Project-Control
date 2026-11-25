"""Build portfolio-wide risk/resource intelligence from the project workspace store."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .project_store import ProjectStore
from .portfolio_risk_resource_intelligence import build_portfolio_risk_resource_view


def build_stored_portfolio_risk_resource_view(database_path: str | Path) -> dict[str, Any]:
    store = ProjectStore(database_path)
    with store._connect() as db:
        project_ids = [row["project_id"] for row in db.execute(
            "SELECT DISTINCT project_id FROM project_records WHERE dataset='project_master' ORDER BY project_id"
        ).fetchall()]
    risks: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    for project_id in project_ids:
        workspace = store.load_project_workspace(project_id)
        if not workspace["project_master"]:
            continue
        master = workspace["project_master"][0]
        currency = str(master.get("currency", "")).strip().upper()
        for risk in workspace["risk"]:
            risks.append({**risk, "project_id": project_id, "currency": currency})
        for resource in workspace["resources"]:
            resources.append({**resource, "project_id": project_id})
    result = build_portfolio_risk_resource_view(risks, resources)
    result["project_count"] = len(project_ids)
    result["data_source"] = "Local ProjectStore SQLite workspace"
    return result
