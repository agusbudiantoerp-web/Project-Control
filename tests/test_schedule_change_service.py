import pytest

from ai_project_control.schedule_change_service import decide_schedule_change


def pending_change():
    return {
        "project_id": "P1", "change_id": "CR-1", "baseline_id": "BL-1",
        "description": "Additional drainage", "status": "PENDING",
        "cost_impact": 1000, "schedule_impact_days": 2,
    }


@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED"])
def test_pending_change_can_receive_auditable_decision(decision):
    source = pending_change()
    result = decide_schedule_change(
        source, decision, "Project Sponsor", "Reviewed against scope and budget",
        decided_at="2026-11-25T12:00:00+00:00",
    )
    assert result["status"] == decision
    assert result["decided_by"] == "Project Sponsor"
    assert result["decision_rationale"]
    assert result["decided_at"] == "2026-11-25T12:00:00+00:00"
    assert source["status"] == "PENDING"


def test_change_decision_requires_reviewer_and_rationale():
    with pytest.raises(ValueError, match="decided_by"):
        decide_schedule_change(pending_change(), "APPROVED", "", "Reviewed")
    with pytest.raises(ValueError, match="rationale"):
        decide_schedule_change(pending_change(), "REJECTED", "Sponsor", " ")


def test_only_pending_change_requests_can_be_decided():
    approved = pending_change()
    approved["status"] = "APPROVED"
    with pytest.raises(ValueError, match="only a PENDING"):
        decide_schedule_change(approved, "REJECTED", "Sponsor", "Reconsidered")


def test_invalid_decision_is_rejected():
    with pytest.raises(ValueError, match="APPROVED or REJECTED"):
        decide_schedule_change(pending_change(), "IMPLEMENTED", "Sponsor", "Accepted")
