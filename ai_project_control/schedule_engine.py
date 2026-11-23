"""Critical Path Method (CPM) schedule analysis for explicit activity networks.

Durations are in working-day units supplied by the caller. This engine does
not apply calendars, holidays, lags, resource leveling, or actual-date logic.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any


def _duration(value: Any, activity_id: str) -> float:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Activity {activity_id}: duration_days must be numeric") from None
    if not math.isfinite(duration) or duration < 0:
        raise ValueError(f"Activity {activity_id}: duration_days must be finite and non-negative")
    return duration


def _predecessors(value: Any, activity_id: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        values = [str(part).strip() for part in value if str(part).strip()]
    else:
        raise ValueError(f"Activity {activity_id}: predecessors must be a list or comma-separated string")
    if len(values) != len(set(values)):
        raise ValueError(f"Activity {activity_id}: duplicate predecessor reference")
    return values


def calculate_critical_path(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate ES/EF/LS/LF/float for a finish-to-start activity network."""
    if not isinstance(activities, list):
        raise TypeError("activities must be a list")
    if not activities:
        return {
            "status": "NO_ACTIVITIES", "activity_count": 0,
            "project_duration_days": None, "critical_path": [],
            "activities": [], "issues": ["No activities supplied."],
        }

    nodes: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(activities):
        if not isinstance(source, dict):
            raise TypeError(f"Activity at index {index} must be a dictionary")
        activity_id = str(source.get("activity_id", "")).strip()
        if not activity_id:
            raise ValueError(f"Activity at index {index}: activity_id is required")
        if activity_id in nodes:
            raise ValueError(f"Duplicate activity_id: {activity_id}")
        nodes[activity_id] = {
            "activity_id": activity_id,
            "name": str(source.get("activity_name", source.get("name", activity_id))),
            "duration": _duration(source.get("duration_days"), activity_id),
            "predecessors": _predecessors(source.get("predecessors", source.get("predecessor_ids")), activity_id),
        }

    issues = []
    for activity_id, node in nodes.items():
        missing = [pred for pred in node["predecessors"] if pred not in nodes]
        if missing:
            issues.append(f"{activity_id} references missing predecessor(s): {', '.join(missing)}")
    if issues:
        return {
            "status": "INVALID_DEPENDENCIES", "activity_count": len(nodes),
            "project_duration_days": None, "critical_path": [],
            "activities": [], "issues": issues,
        }

    successors: dict[str, list[str]] = defaultdict(list)
    indegree = {activity_id: 0 for activity_id in nodes}
    for activity_id, node in nodes.items():
        for predecessor in node["predecessors"]:
            successors[predecessor].append(activity_id)
            indegree[activity_id] += 1

    queue = deque(sorted(activity_id for activity_id, degree in indegree.items() if degree == 0))
    order = []
    while queue:
        activity_id = queue.popleft()
        order.append(activity_id)
        for successor in sorted(successors[activity_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(order) != len(nodes):
        cyclic = sorted(activity_id for activity_id, degree in indegree.items() if degree > 0)
        return {
            "status": "CYCLIC_DEPENDENCIES", "activity_count": len(nodes),
            "project_duration_days": None, "critical_path": [],
            "activities": [], "issues": [f"Dependency cycle detected involving: {', '.join(cyclic)}"],
        }

    es: dict[str, float] = {}
    ef: dict[str, float] = {}
    for activity_id in order:
        node = nodes[activity_id]
        es[activity_id] = max((ef[pred] for pred in node["predecessors"]), default=0.0)
        ef[activity_id] = es[activity_id] + node["duration"]

    project_duration = max(ef.values())
    lf: dict[str, float] = {}
    ls: dict[str, float] = {}
    for activity_id in reversed(order):
        following = successors[activity_id]
        lf[activity_id] = min((ls[item] for item in following), default=project_duration)
        ls[activity_id] = lf[activity_id] - nodes[activity_id]["duration"]

    results = []
    critical_path = []
    for activity_id in order:
        total_float = max(0.0, ls[activity_id] - es[activity_id])
        critical = math.isclose(total_float, 0.0, abs_tol=1e-9)
        if critical:
            critical_path.append(activity_id)
        results.append({
            "activity_id": activity_id,
            "activity_name": nodes[activity_id]["name"],
            "duration_days": nodes[activity_id]["duration"],
            "predecessors": nodes[activity_id]["predecessors"],
            "early_start": round(es[activity_id], 3),
            "early_finish": round(ef[activity_id], 3),
            "late_start": round(ls[activity_id], 3),
            "late_finish": round(lf[activity_id], 3),
            "total_float_days": round(total_float, 3),
            "is_critical": critical,
        })

    return {
        "status": "ASSESSED",
        "activity_count": len(nodes),
        "project_duration_days": round(project_duration, 3),
        "critical_path": critical_path,
        "activities": results,
        "issues": [],
        "assumptions": [
            "Finish-to-start relationships with zero lag are assumed.",
            "Durations are supplied in a single consistent working-day unit.",
            "No calendars, holidays, constraints, resource leveling or actual progress are applied.",
            "Multiple critical paths may exist; critical_path lists all zero-float activities in topological order, not necessarily one unique chain.",
        ],
    }
