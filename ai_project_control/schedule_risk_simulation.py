"""Monte Carlo schedule duration forecast with activity-linked risk events.

Uses an explicit activity network and triangular duration distributions.
No working calendar or risk correlation is inferred.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from typing import Any


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric") from None
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _triangular(rng: random.Random, low: float, mode: float, high: float) -> float:
    """Sample a triangular distribution, including a valid zero-width point mass."""
    if low == high:
        return low
    return rng.triangular(low, high, mode)


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _topological_order(activities: list[dict[str, Any]]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    records: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(activities):
        if not isinstance(row, dict):
            raise TypeError(f"activity {index} must be a dictionary")
        aid = str(row.get("activity_id", "")).strip()
        if not aid or aid in records:
            raise ValueError("activity_id is required and must be unique")
        predecessors = row.get("predecessors", [])
        if not isinstance(predecessors, list) or any(not isinstance(x, str) for x in predecessors):
            raise ValueError(f"{aid}: predecessors must be a list of activity IDs")
        records[aid] = {**row, "activity_id": aid, "predecessors": predecessors}

    for aid, row in records.items():
        unknown = set(row["predecessors"]) - records.keys()
        if unknown:
            raise ValueError(f"{aid}: unknown predecessors: {', '.join(sorted(unknown))}")
        if aid in row["predecessors"]:
            raise ValueError(f"{aid}: activity cannot depend on itself")

    incoming = {aid: len(row["predecessors"]) for aid, row in records.items()}
    outgoing = {aid: [] for aid in records}
    for aid, row in records.items():
        for pred in row["predecessors"]:
            outgoing[pred].append(aid)
    ready = sorted(aid for aid, count in incoming.items() if count == 0)
    order = []
    while ready:
        aid = ready.pop(0)
        order.append(aid)
        for nxt in sorted(outgoing[aid]):
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    if len(order) != len(records):
        raise ValueError("activity network contains a dependency cycle")
    return order, records


def simulate_schedule_risk(
    activities: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    project_start_date: str | date,
    *,
    iterations: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """Simulate project finish dates and activity-linked risk delay exposure.

    Activity fields: activity_id, predecessors, duration_min_days,
    duration_most_likely_days, duration_max_days.
    Risk fields: risk_id, activity_id, probability, delay_min_days,
    delay_most_likely_days, delay_max_days.
    """
    if not isinstance(activities, list) or not isinstance(risks, list):
        raise TypeError("activities and risks must be lists")
    if not isinstance(iterations, int) or isinstance(iterations, bool) or not 1000 <= iterations <= 200000:
        raise ValueError("iterations must be an integer from 1000 to 200000")
    try:
        if isinstance(project_start_date, datetime):
            start = project_start_date.date()
        else:
            start = project_start_date if isinstance(project_start_date, date) else date.fromisoformat(str(project_start_date))
    except ValueError:
        raise ValueError("project_start_date must be YYYY-MM-DD") from None
    if not activities:
        return {"status": "NO_ACTIVITIES", "iterations": iterations, "risk_count": len(risks)}

    order, records = _topological_order(activities)
    durations = {}
    for aid, row in records.items():
        low = _finite(row.get("duration_min_days"), f"{aid}.duration_min_days")
        mode = _finite(row.get("duration_most_likely_days"), f"{aid}.duration_most_likely_days")
        high = _finite(row.get("duration_max_days"), f"{aid}.duration_max_days")
        if low < 0 or not low <= mode <= high:
            raise ValueError(f"{aid}: durations must satisfy 0 <= min <= most_likely <= max")
        durations[aid] = (low, mode, high)

    parsed_risks = []
    seen = set()
    for index, row in enumerate(risks):
        if not isinstance(row, dict):
            raise TypeError(f"risk {index} must be a dictionary")
        rid = str(row.get("risk_id", "")).strip()
        aid = str(row.get("activity_id", "")).strip()
        if not rid or rid in seen:
            raise ValueError("risk_id is required and must be unique")
        seen.add(rid)
        if aid not in records:
            raise ValueError(f"{rid}: activity_id must reference a known activity")
        probability = _finite(row.get("probability"), f"{rid}.probability")
        low = _finite(row.get("delay_min_days"), f"{rid}.delay_min_days")
        mode = _finite(row.get("delay_most_likely_days"), f"{rid}.delay_most_likely_days")
        high = _finite(row.get("delay_max_days"), f"{rid}.delay_max_days")
        if not 0 <= probability <= 1 or low < 0 or not low <= mode <= high:
            raise ValueError(f"{rid}: probability must be 0..1 and delays 0 <= min <= most_likely <= max")
        parsed_risks.append((aid, probability, low, mode, high))

    # Independent streams preserve common random numbers: adding a risk event
    # must not perturb the sampled baseline activity durations.
    duration_rng = random.Random(seed)
    risk_rng = random.Random(seed ^ 0x5F3759DF)
    terminal_activities = [
        aid for aid in order
        if not any(aid in row["predecessors"] for row in records.values())
    ]
    finishes = []
    for _ in range(iterations):
        sampled = {
            aid: _triangular(duration_rng, low, mode, high)
            for aid, (low, mode, high) in durations.items()
        }
        for aid, probability, low, mode, high in parsed_risks:
            if risk_rng.random() < probability:
                sampled[aid] += _triangular(risk_rng, low, mode, high)
                if not math.isfinite(sampled[aid]):
                    raise ValueError("Sampled activity duration exceeds the supported numeric range")
        earliest_finish = {}
        for aid in order:
            predecessor_finish = max((earliest_finish[p] for p in records[aid]["predecessors"]), default=0.0)
            earliest_finish[aid] = predecessor_finish + sampled[aid]
            if not math.isfinite(earliest_finish[aid]):
                raise ValueError("Simulated schedule duration exceeds the supported numeric range")
        finishes.append(max((earliest_finish[aid] for aid in terminal_activities), default=0.0))

    p50, p80, p90 = (_percentile(finishes, p) for p in (.5, .8, .9))
    probability_target = {}
    for target_days in sorted(set(math.ceil(p) for p in (p50, p80, p90))):
        probability_target[(start + timedelta(days=target_days)).isoformat()] = round(
            sum(value <= target_days for value in finishes) / iterations * 100, 2
        )
    def date_at(days: float) -> str:
        return (start + timedelta(days=math.ceil(days))).isoformat()

    return {
        "status": "ASSESSED",
        "iterations": iterations,
        "seed": seed,
        "activity_count": len(records),
        "risk_count": len(parsed_risks),
        "project_start_date": start.isoformat(),
        "duration_days": {
            "p50": round(p50, 2), "p80": round(p80, 2), "p90": round(p90, 2),
        },
        "finish_date": {
            "p50": date_at(p50), "p80": date_at(p80), "p90": date_at(p90),
        },
        "probability_finish_by": probability_target,
        "limitations": [
            "Activity durations and risk delay impacts use triangular distributions.",
            "Risk events are independent; correlation and common-cause effects are not modeled.",
            "Only risk events linked to a valid activity are included.",
            "Dependencies are finish-to-start with no leads, lags, calendars or resource constraints.",
            "Durations are calendar days; holidays and contractual working calendars are not applied.",
            "P50/P80/P90 are simulation percentiles, not guarantees or approved baseline changes.",
        ],
    }
