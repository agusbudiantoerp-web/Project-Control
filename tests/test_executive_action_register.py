from datetime import date, timedelta

import pytest

from ai_project_control.executive_action_register import (
    build_action_register, create_action, transition_action,
)


def _action(**overrides):
    data = dict(
        title="Recover critical path",
        owner="Project Manager",
        due_date=date.today() + timedelta(days=7),
        project_id="PRJ-001",
        priority="P1",
        created_by="Director",
    )
    data.update(overrides)
    return create_action(**data)


def test_create_action_validates_required_fields_and_normalizes_priority():
    action = _action(priority="p1")
    assert action["priority"] == "P1"
    assert action["status"] == "OPEN"
    assert action["project_id"] == "PRJ-001"


@pytest.mark.parametrize("field,value", [
    ("title", ""), ("owner", " "), ("project_id", ""), ("created_by", ""),
])
def test_create_action_rejects_missing_required_fields(field, value):
    with pytest.raises(ValueError):
        _action(**{field: value})


def test_create_action_rejects_invalid_due_date_and_priority():
    with pytest.raises(ValueError, match="due_date"):
        _action(due_date="not-a-date")
    with pytest.raises(ValueError, match="priority"):
        _action(priority="URGENT")


def test_transition_returns_new_action_and_audit_event_without_mutating_input():
    original = _action()
    updated, event = transition_action(
        original, new_status="IN_PROGRESS", changed_by="PM",
        note="Recovery plan approved", occurred_at="2026-11-23T04:00:00+00:00",
    )
    assert original["status"] == "OPEN"
    assert updated["status"] == "IN_PROGRESS"
    assert event["from_status"] == "OPEN"
    assert event["to_status"] == "IN_PROGRESS"
    assert event["changed_by"] == "PM"


def test_terminal_status_cannot_be_reopened():
    completed, _ = transition_action(_action(), new_status="IN_PROGRESS", changed_by="PM")
    completed, _ = transition_action(completed, new_status="COMPLETED", changed_by="PM")
    with pytest.raises(ValueError, match="not allowed"):
        transition_action(completed, new_status="OPEN", changed_by="PM")


def test_register_sorts_priorities_and_counts_blocked_actions():
    p3 = _action(action_id="A3", priority="P3")
    p1 = _action(action_id="A1", priority="P1")
    blocked, event = transition_action(_action(action_id="A2"), new_status="BLOCKED", changed_by="PM")
    result = build_action_register([p3, blocked, p1], [event])
    assert [row["action_id"] for row in result["actions"]] == ["A1", "A2", "A3"]
    assert result["summary"]["blocked_count"] == 1
    assert result["summary"]["action_count"] == 3
    assert len(result["events"]) == 1


def test_register_rejects_duplicate_action_ids():
    with pytest.raises(ValueError, match="unique"):
        build_action_register([_action(action_id="DUP"), _action(action_id="DUP")])
