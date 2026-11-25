from datetime import date, timedelta

import pytest

from ai_project_control.action_register_store import ActionRegisterStore


def test_action_is_persisted_and_visible_after_reopening_store(tmp_path):
    path = tmp_path / "actions.sqlite3"
    store = ActionRegisterStore(path)
    created = store.create(
        title="Recover critical path", owner="Project Manager",
        due_date=date.today() + timedelta(days=3), project_id="P-01",
        created_by="Director", priority="P1", action_id="A-01", risk_id="R-01",
    )
    reopened = ActionRegisterStore(path)
    register = reopened.list_project("P-01")
    assert register["summary"]["action_count"] == 1
    assert register["actions"][0]["action_id"] == created["action_id"]
    assert register["actions"][0]["status"] == "OPEN"
    assert register["actions"][0]["risk_id"] == "R-01"


def test_transition_and_audit_event_commit_together(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite3")
    store.create(
        title="Resolve equipment shortage", owner="Site Manager",
        due_date=date.today() + timedelta(days=1), project_id="P-02",
        created_by="PM", action_id="A-02",
    )
    updated, event = store.transition(
        "A-02", new_status="IN_PROGRESS", changed_by="Site Manager",
        note="Supplier mobilization confirmed",
    )
    result = store.list_project("P-02")
    assert updated["status"] == "IN_PROGRESS"
    assert result["summary"]["in_progress_count"] == 1
    assert result["events"][0]["event_id"] == event["event_id"]


def test_invalid_transition_does_not_append_event_or_change_status(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite3")
    store.create(
        title="Approve recovery plan", owner="Director",
        due_date=date.today(), project_id="P-03",
        created_by="PM", action_id="A-03",
    )
    with pytest.raises(ValueError, match="not allowed"):
        store.transition("A-03", new_status="COMPLETED", changed_by="PM")
    result = store.list_project("P-03")
    assert result["actions"][0]["status"] == "OPEN"
    assert result["events"] == []


def test_missing_action_raises_key_error(tmp_path):
    store = ActionRegisterStore(tmp_path / "actions.sqlite3")
    with pytest.raises(KeyError, match="not found"):
        store.transition("UNKNOWN", new_status="IN_PROGRESS", changed_by="PM")


def test_in_memory_action_store_persists_across_connections_and_closes():
    store = ActionRegisterStore(":memory:")
    store.create(
        title="Test memory action", owner="PM", due_date=date.today(),
        project_id="P-MEM", created_by="Director", action_id="A-MEM",
    )
    assert store.list_project("P-MEM")["summary"]["action_count"] == 1
    store.close()
    with pytest.raises(RuntimeError, match="ActionRegisterStore is closed"):
        store.list_project("P-MEM")
