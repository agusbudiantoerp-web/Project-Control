"""Critical Path Method (CPM) for FS, SS, FF and SF activity relationships.

Durations and relationship lags use one consistent working-day unit. The
engine does not apply calendars, holidays, constraints, resource leveling,
actual-date logic or native Primavera calendar semantics.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

_RELATIONSHIPS = {"FS", "SS", "FF", "SF"}


def _number(value: Any, label: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric") from None
    if not math.isfinite(number) or (non_negative and number < 0):
        qualifier = "finite and non-negative" if non_negative else "finite"
        raise ValueError(f"{label} must be {qualifier}")
    return number


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


def _relationship_offset(kind: str, lag: float, predecessor_duration: float,
                         successor_duration: float) -> float:
    if kind == "FS":
        return predecessor_duration + lag
    if kind == "SS":
        return lag
    if kind == "FF":
        return predecessor_duration + lag - successor_duration
    return lag - successor_duration  # SF


def calculate_critical_path(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate ES/EF/LS/LF/float while honoring each supplied relationship."""
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
        duration = _number(source.get("duration_days"), f"Activity {activity_id}: duration_days", non_negative=True)
        raw_relationships = source.get("predecessor_relationships")
        relationships = []
        if raw_relationships not in (None, ""):
            if not isinstance(raw_relationships, list):
                raise ValueError(f"Activity {activity_id}: predecessor_relationships must be a list")
            for rel_index, rel in enumerate(raw_relationships):
                if not isinstance(rel, dict):
                    raise ValueError(f"Activity {activity_id}: relationship {rel_index} must be an object")
                predecessor = str(rel.get("predecessor_id", "")).strip()
                kind = str(rel.get("relationship_type", "FS")).strip().upper()
                if kind.startswith("PR_"):
                    kind = kind[3:]
                if not predecessor:
                    raise ValueError(f"Activity {activity_id}: relationship predecessor_id is required")
                if kind not in _RELATIONSHIPS:
                    raise ValueError(f"Activity {activity_id}: unsupported relationship type {kind}")
                lag = _number(rel.get("lag_days", 0), f"Activity {activity_id}: relationship lag_days")
                relationships.append({
                    "predecessor_id": predecessor,
                    "relationship_type": kind,
                    "lag_days": lag,
                })
        else:
            relationships = [
                {"predecessor_id": predecessor, "relationship_type": "FS", "lag_days": 0.0}
                for predecessor in _predecessors(source.get("predecessors", source.get("predecessor_ids")), activity_id)
            ]
        nodes[activity_id] = {
            "activity_id": activity_id,
            "name": str(source.get("activity_name", source.get("name", activity_id))),
            "duration": duration,
            "relationships": relationships,
        }

    issues = []
    for activity_id, node in nodes.items():
        missing = sorted({r["predecessor_id"] for r in node["relationships"] if r["predecessor_id"] not in nodes})
        if missing:
            issues.append(f"{activity_id} references missing predecessor(s): {', '.join(missing)}")
        self_links = [r for r in node["relationships"] if r["predecessor_id"] == activity_id]
        if self_links:
            issues.append(f"{activity_id} cannot depend on itself")
    if issues:
        return {
            "status": "INVALID_DEPENDENCIES", "activity_count": len(nodes),
            "project_duration_days": None, "critical_path": [],
            "activities": [], "issues": issues,
        }

    successors: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    graph_successors: dict[str, set[str]] = defaultdict(set)
    indegree = {activity_id: 0 for activity_id in nodes}
    for activity_id, node in nodes.items():
        for rel in node["relationships"]:
            predecessor = rel["predecessor_id"]
            successors[predecessor].append((activity_id, rel))
            if activity_id not in graph_successors[predecessor]:
                graph_successors[predecessor].add(activity_id)
                indegree[activity_id] += 1

    queue = deque(sorted(activity_id for activity_id, degree in indegree.items() if degree == 0))
    order = []
    while queue:
        activity_id = queue.popleft()
        order.append(activity_id)
        for successor in sorted(graph_successors[activity_id]):
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
        constraints = []
        for rel in node["relationships"]:
            predecessor = rel["predecessor_id"]
            offset = _relationship_offset(
                rel["relationship_type"], rel["lag_days"],
                nodes[predecessor]["duration"], node["duration"],
            )
            constraints.append(es[predecessor] + offset)
        es[activity_id] = max(0.0, max(constraints, default=0.0))
        ef[activity_id] = es[activity_id] + node["duration"]
        if not math.isfinite(ef[activity_id]):
            raise ValueError("Schedule duration overflowed the supported numeric range")

    project_duration = max(ef.values())
    ls: dict[str, float] = {}
    lf: dict[str, float] = {}
    for activity_id in reversed(order):
        limits = []
        for successor, rel in successors[activity_id]:
            offset = _relationship_offset(
                rel["relationship_type"], rel["lag_days"],
                nodes[activity_id]["duration"], nodes[successor]["duration"],
            )
            limits.append(ls[successor] - offset)
        # Every activity must finish no later than the overall project finish,
        # even when its outgoing links are SS/SF and do not constrain its finish.
        limits.append(project_duration - nodes[activity_id]["duration"])
        ls[activity_id] = min(limits)
        lf[activity_id] = ls[activity_id] + nodes[activity_id]["duration"]

    results = []
    critical_path = []
    for activity_id in order:
        total_float = ls[activity_id] - es[activity_id]
        if abs(total_float) < 1e-9:
            total_float = 0.0
        critical = math.isclose(total_float, 0.0, abs_tol=1e-9)
        if critical:
            critical_path.append(activity_id)
        node = nodes[activity_id]
        results.append({
            "activity_id": activity_id,
            "activity_name": node["name"],
            "duration_days": node["duration"],
            "predecessors": sorted({r["predecessor_id"] for r in node["relationships"]}),
            "predecessor_relationships": [dict(r) for r in node["relationships"]],
            "early_start": round(es[activity_id], 6),
            "early_finish": round(ef[activity_id], 6),
            "late_start": round(ls[activity_id], 6),
            "late_finish": round(lf[activity_id], 6),
            "total_float_days": round(total_float, 6),
            "is_critical": critical,
        })

    return {
        "status": "ASSESSED",
        "activity_count": len(nodes),
        "project_duration_days": round(project_duration, 6),
        "critical_path": critical_path,
        "activities": results,
        "issues": [],
        "assumptions": [
            "FS, SS, FF and SF relationships are honored with signed lag/lead in the supplied day unit.",
            "P6 lag hours must be converted by the caller using the selected nominal hours-per-day convention.",
            "Durations and lags use one consistent working-day unit; no calendars or holidays are applied.",
            "No constraints, resource leveling or actual progress are applied.",
            "Multiple critical paths may exist; critical_path lists all zero-float activities in topological order.",
        ],
    }
