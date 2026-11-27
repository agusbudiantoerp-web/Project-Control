"""Central configuration for the primary local project workspace."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_WORKSPACE_DATABASE = ".project_control/project_control.sqlite3"


def get_workspace_database_path() -> str:
    """Return the one configured SQLite path shared by every primary app page."""
    configured = os.getenv("PROJECT_CONTROL_DB", DEFAULT_WORKSPACE_DATABASE).strip()
    if not configured:
        configured = DEFAULT_WORKSPACE_DATABASE
    return str(Path(configured).expanduser())
