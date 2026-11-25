"""Critical Path Method analysis for FS/SS/FF/SF activity relationships.

Durations and lags are expressed in one consistent working-day unit. This
engine is calendar-neutral: it does not apply weekends, holidays, constraints,
resource leveling, or Primavera's native calendar calculations.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

_RELATION_TYPES = {"FS", "SS", "FF", "SF"}


def _finite(value: Any, label: str, *, non_negative: bool = False) -> float:
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


def _activity_relationships(source: dict[str, Any], activity_id: str) -> list[dict[str, Any]]:
    raw = source.get("relationship_details", source.get("relationships"))
    if raw is None:
        return [
            {"predecessor_id": predecessor, "type": "FS", "lag_days": 0.0}
            for predecessor in _predecessors(
                source.get("predecessors", source.get("predecessor_ids")), activity_id
            )
        ]
    if not isinstance(raw, list):
        raise ValueError(f"Activity {activity_id}: relationship_details must be a list")
    relationships = []
    seen = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Activity {activity_id}: relationship {index + 1} must be an object")
        predecessor = str(item.get("predecessor_id", item.get("pred_activity_id", ""))).strip()
        if not predecessor:
            raise ValueError(f"Activity {activity_id}: relationship predecessor_id is required")
        relation_type = str(item.get("type", item.get("relationship_type", "FS"))).strip().upper()
        if relation_type.startswith("PR_"):
            relation_type = relation_type[3:]
        if relation_type not in _RELATION_TYPES:
            raise ValueError(f"Activity {activity_id}: unsupported relationship type {relation_type}")
        lag = _finite(item.get("lag_days", 0), f"Activity {activity_id} relationship lag_days")
        key = (predecessor, relation_type, lag)
        if key in seen:
            raise ValueError(f"Activity {activity_id}: duplicate relationship")
        seen.add(key)
        relationships.append({
            "predecessor_id": predecessor, "type": relation_type, "lag_days": lag,
        })
    return relationships


def _relationship_offset(relation: dict[str, Any], predecessor_duration: float, successor_duration: float) -> float:
    """Convert a P6 relation into the equivalent successor-start constraint."""
    relation_type = relation["type"]
    lag = relation["lag_days"]
    if relation_type == "FS":
        return predecessor_duration + lag
    if relation_type == "SS":
        return lag
    if relation_type == "FF":
        return predecessor_duration + lag - successor_duration
    return lag - successor_duration  # SF


def calculate_critical_path(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate ES/EF/LS/LF/float for a typed activity relationship network."""
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
            "duration": _finite(source.get("duration_days"), f"Activity {activity_id} duration_days", non_negative=True),
            "relationships": _activity_relationships(source, activity_id),
        }

    issues = []
    successors: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    indegree = {activity_id: 0 for activity_id in nodes}
    for activity_id, node in nodes.items():
        seen_predecessors = set()
        for relation in node["relationships"]:
            predecessor = relation["predecessor_id"]
            if predecessor not in nodes:
                issues.append(f"{activity_id} references missing predecessor: {predecessor}")
                continue
            if predecessor == activity_id:
                issues.append(f"{activity_id} cannot depend on itself")
                continue
            if predecessor in seen_predecessors:
                issues.append(f"{activity_id} has multiple relationship types to {predecessor}; consolidate to one relationship")
                continue
            seen_predecessors.add(predecessor)
            successors[predecessor].append((activity_id, relation))
            indegree[activity_id] += 1
    if issues:
        return {
            "status": "INVALID_DEPENDENCIES", "activity_count": len(nodes),
            "project_duration_days": None, "critical_path": [],
            "activities": [], "issues": issues,
        }

    queue = deque(sorted(activity_id for activity_id, degree in indegree.items() if degree == 0))
    order = []
    while queue:
        activity_id = queue.popleft()
        order.append(activity_id)
        for successor, _ in sorted(successors[activity_id], key=lambda item: item[0]):
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
        candidates = []
        for relation in node["relationships"]:
            predecessor = relation["predecessor_id"]
            offset = _relationship_offset(relation, nodes[predecessor]["duration"], node["duration"])
            candidates.append(es[predecessor] + offset)
        es[activity_id] = max([0.0, *candidates])
        ef[activity_id] = es[activity_id] + node["duration"]
        if not math.isfinite(ef[activity_id]):
            raise ValueError("Schedule duration overflowed the supported numeric range")

    project_duration = max(ef.values())
    ls = {activity_id: project_duration - nodes[activity_id]["duration"] for activity_id in nodes}
    for activity_id in reversed(order):
        for successor, relation in successors[activity_id]:
            offset = _relationship_offset(
                relation, nodes[activity_id]["duration"], nodes[successor]["duration"]
            )
            ls[activity_id] = min(ls[activity_id], ls[successor] - offset)

    results = []
    critical_path = []
    for activity_id in order:
        node = nodes[activity_id]
        total_float = ls[activity_id] - es[activity_id]
        if not math.isfinite(total_float):
            raise ValueError("Schedule float overflowed the supported numeric range")
        critical = math.isclose(total_float, 0.0, abs_tol=1e-9)
        if critical:
            critical_path.append(activity_id)
        relationships = [dict(item) for item in node["relationships"]]
        results.append({
            "activity_id": activity_id,
            "activity_name": node["name"],
            "duration_days": node["duration"],
            "predecessors": [item["predecessor_id"] for item in relationships],
            "relationships": relationships,
            "early_start": round(es[activity_id], 3),
            "early_finish": round(ef[activity_id], 3),
            "late_start": round(ls[activity_id], 3),
            "late_finish": round(ls[activity_id] + node["duration"], 3),
            "total_float_days": round(max(0.0, total_float), 3),
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
            "FS, SS, FF and SF relationships are supported with signed lag in working-day units.",
            "Legacy predecessor_ids are interpreted as FS relationships with zero lag.",
            "Durations and lags use one consistent working-day unit.",
            "No calendars, holidays, constraints, resource leveling or actual progress are applied.",
            "Multiple critical paths may exist; critical_path lists zero-float activities in topological order, not necessarily one unique chain.",
        ],
    }
