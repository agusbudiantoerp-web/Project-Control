import pytest

from ai_project_control.risk_governance_bridge import build_risk_governance_view


def test_risk_governance_joins_linked_actions_and_mitigation():
    result = build_risk_governance_view(
        [{"risk_id": "R1", "description": "Long lead equipment", "risk_owner": "Procurement"}],
        [
            {"action_id": "A1", "risk_id": "R1", "status": "BLOCKED", "due_date": "2026-11-01"},
            {"action_id": "A2", "risk_id": "R1", "status": "COMPLETED", "due_date": "2026-10-01"},
            {"action_id": "A3", "risk_id": "R-UNKNOWN", "status": "OPEN", "due_date": "2026-11-01"},
        ],
        [{
            "risk_id": "R1", "status": "IN_PROGRESS", "owner": "Procurement Lead",
            "due_date": "2026-12-01", "residual_exposure": 25, "evidence": "",
        }],
        as_of_date="2026-11-24",
    )
    assert result["status"] == "ASSESSED"
    assert result["risks_requiring_attention"] == 1
    assert result["overdue_action_count"] == 1
    assert result["blocked_action_count"] == 1
    assert result["orphan_action_count"] == 1
    row = result["rows"][0]
    assert row["linked_action_count"] == 2
    assert row["active_action_count"] == 1
    assert row["mitigation_status"] == "IN_PROGRESS"
    assert row["residual_exposure"] == 25


def test_risk_without_mitigation_requires_attention():
    result = build_risk_governance_view(
        [{"risk_id": "R1"}], [], [], as_of_date="2026-11-24"
    )
    assert result["risks_without_mitigation"] == 1
    assert result["rows"][0]["governance_attention"] is True


def test_empty_risk_register_and_invalid_inputs():
    assert build_risk_governance_view([], [], [])["status"] == "NO_RISKS"
    with pytest.raises(ValueError, match="unique"):
        build_risk_governance_view([{"risk_id": "R1"}, {"risk_id": "R1"}], [], [])
    with pytest.raises(ValueError, match="as_of_date"):
        build_risk_governance_view([], [], [], as_of_date="not-a-date")
    with pytest.raises(TypeError):
        build_risk_governance_view({}, [], [])
