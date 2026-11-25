from datetime import date

import pytest

from ai_project_control.action_escalation import build_action_escalations


def _row(action_id, **overrides):
    row = {
        "action_id": action_id,
        "project_id": "PRJ-01",
        "title": "Resolve critical delay",
        "owner": "Project Manager",
        "priority": "P1",
        "status": "OPEN",
        "due_date": "2026-11-20",
    }
    row.update(overrides)
    return row


def test_overdue_p1_is_escalated_to_project_director():
    result = build_action_escalations([_row("A1")], as_of="2026-11-23")
    item = result["escalations"][0]
    assert item["reason"] == "P1_ACTION_OVERDUE"
    assert item["escalation_level"] == "PROJECT_DIRECTOR"
    assert item["overdue_days"] == 3


def test_blocked_p1_is_escalated_even_when_not_overdue():
    result = build_action_escalations(
        [_row("A1", status="BLOCKED", due_date="2026-11-25")],
        as_of=date(2026, 11, 23),
    )
    assert result["escalations"][0]["reason"] == "P1_ACTION_BLOCKED"


def test_non_p1_overdue_action_goes_to_project_manager():
    result = build_action_escalations(
        [_row("A2", priority="P2")], as_of="2026-11-23"
    )
    assert result["escalations"][0]["escalation_level"] == "PROJECT_MANAGER"


def test_due_today_and_future_actions_are_not_overdue():
    rows = [_row("TODAY", due_date="2026-11-23"), _row("FUTURE", due_date="2026-11-24")]
    result = build_action_escalations(rows, as_of="2026-11-23")
    assert result["status"] == "NO_ESCALATIONS"


def test_completed_and_cancelled_actions_are_excluded():
    rows = [_row("DONE", status="COMPLETED"), _row("CANCEL", status="CANCELLED")]
    assert build_action_escalations(rows, as_of="2026-11-23")["escalations"] == []


def test_missing_due_date_is_unassessed_not_overdue():
    result = build_action_escalations([_row("NO-DATE", due_date=None)], as_of="2026-11-23")
    assert result["escalations"][0]["reason"] == "DUE_DATE_UNASSESSED"
    assert result["escalations"][0]["overdue_days"] == 0


def test_invalid_as_of_is_rejected():
    with pytest.raises(ValueError, match="as_of"):
        build_action_escalations([], as_of="yesterday")
