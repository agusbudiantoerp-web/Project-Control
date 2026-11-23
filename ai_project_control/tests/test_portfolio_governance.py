import json
import pandas as pd
import pytest

from portfolio_governance import (
    submit_recovery_action, transition_recovery_action, governance_summary,
)


def _submitted():
    result = submit_recovery_action(
        pd.DataFrame(), project_id="PRJ-01", scenario="Crash option A",
        recovery_action="Add second shift on critical activity",
        owner="Site Manager", requested_by="Planner",
        proposed_budget=125000, currency="IDR",
    )
    return result["register"], result["request_id"]


def test_submit_creates_proposed_with_audit_event():
    register, request_id = _submitted()
    row = register.iloc[0]
    assert row["request_id"] == request_id
    assert row["status"] == "Proposed"
    assert json.loads(row["decision_history"])[0]["to"] == "Proposed"


def test_approval_chain_requires_correct_roles():
    register, request_id = _submitted()
    with pytest.raises(PermissionError):
        transition_recovery_action(register, request_id, "PM Approved", "Alex", "COO")
    register = transition_recovery_action(register, request_id, "PM Approved", "PM", "Project Manager")
    register = transition_recovery_action(register, request_id, "Director Approved", "PD", "Project Director")
    register = transition_recovery_action(register, request_id, "COO Approved", "COO", "COO")
    assert register.iloc[0]["status"] == "COO Approved"
    assert pd.notna(register.iloc[0]["coo_approved_at"])


def test_cannot_skip_approval_stages():
    register, request_id = _submitted()
    with pytest.raises(ValueError):
        transition_recovery_action(register, request_id, "COO Approved", "COO", "COO")


def test_rejection_and_closure_require_evidence():
    register, request_id = _submitted()
    with pytest.raises(ValueError):
        transition_recovery_action(register, request_id, "Rejected", "PM", "Project Manager")
    register = transition_recovery_action(register, request_id, "Rejected", "PM", "Project Manager", "Safety risk not mitigated")
    with pytest.raises(ValueError):
        transition_recovery_action(register, request_id, "Closed", "PM", "Project Manager", "Cannot reopen rejected request")


def test_source_register_is_not_mutated():
    register, request_id = _submitted()
    before = register.copy(deep=True)
    transition_recovery_action(register, request_id, "PM Approved", "PM", "Project Manager")
    pd.testing.assert_frame_equal(register, before)


def test_currency_budget_and_required_fields_validated():
    with pytest.raises(ValueError):
        submit_recovery_action(pd.DataFrame(), project_id="", scenario="A",
            recovery_action="Action", owner="Owner", requested_by="User",
            proposed_budget=100, currency="IDR")
    with pytest.raises(ValueError):
        submit_recovery_action(pd.DataFrame(), project_id="P", scenario="A",
            recovery_action="Action", owner="Owner", requested_by="User",
            proposed_budget=-1, currency="IDR")


def test_governance_summary_counts_each_status():
    register, request_id = _submitted()
    assert governance_summary(register)["Proposed"] == 1



def test_rejection_authority_follows_current_approval_stage():
    register, request_id = _submitted()
    register = transition_recovery_action(register, request_id, "PM Approved", "PM", "Project Manager")
    with pytest.raises(PermissionError):
        transition_recovery_action(register, request_id, "Rejected", "PM", "Project Manager", "Not accepted")
    register = transition_recovery_action(register, request_id, "Rejected", "Director", "Project Director", "Insufficient schedule evidence")
    assert register.iloc[0]["status"] == "Rejected"


def test_fully_approved_action_can_start_and_close_with_evidence():
    register, request_id = _submitted()
    register = transition_recovery_action(register, request_id, "PM Approved", "PM", "Project Manager")
    register = transition_recovery_action(register, request_id, "Director Approved", "PD", "Project Director")
    register = transition_recovery_action(register, request_id, "COO Approved", "COO", "COO")
    register = transition_recovery_action(register, request_id, "In Progress", "PM", "Project Manager")
    with pytest.raises(ValueError):
        transition_recovery_action(register, request_id, "Closed", "PM", "Project Manager")
    register = transition_recovery_action(register, request_id, "Closed", "PM", "Project Manager", "Field completion evidence attached")
    assert register.iloc[0]["status"] == "Closed"
    history = json.loads(register.iloc[0]["decision_history"])
    assert [event["to"] for event in history] == [
        "Proposed", "PM Approved", "Director Approved", "COO Approved", "In Progress", "Closed"
    ]


def test_portfolio_overview_consolidates_projects_and_separates_currencies():
    from portfolio_governance import build_portfolio_governance_overview

    first, _ = _submitted()
    second, _ = _submitted()
    second.loc[:, "project_id"] = "PRJ-02"
    second.loc[:, "currency"] = "USD"
    second.loc[:, "proposed_budget"] = 500
    result = build_portfolio_governance_overview(
        {"PRJ-01": first, "PRJ-02": second},
        portfolio=pd.DataFrame([
            {"project_id": "PRJ-01", "project_name": "Bridge", "portfolio_status": "Critical"},
            {"project_id": "PRJ-02", "project_name": "Plant", "portfolio_status": "At Risk"},
        ]),
        risk_register=pd.DataFrame([
            {"project_id": "PRJ-01", "risk_score": 80, "risk_status": "Critical"},
            {"project_id": "PRJ-02", "risk_score": 55, "risk_status": "High"},
        ]),
    )
    assert result["available"] is True
    assert len(result["decision_queue"]) == 2
    assert set(result["budget_by_currency"]["currency"]) == {"IDR", "USD"}
    assert result["budget_by_currency"]["active_budget"].sum() == 125500
    assert result["decision_queue"].iloc[0]["risk_score"] == 80


def test_portfolio_overview_handles_missing_risk_and_optional_fields():
    from portfolio_governance import build_portfolio_governance_overview

    register, _ = _submitted()
    result = build_portfolio_governance_overview({"PRJ-01": register})
    assert result["available"] is True
    assert result["decision_queue"]["risk_score"].isna().all()
    assert result["decision_queue"]["request_age_days"].notna().all()


def test_portfolio_overview_empty_registers_returns_unavailable():
    from portfolio_governance import build_portfolio_governance_overview

    result = build_portfolio_governance_overview({"PRJ-01": pd.DataFrame()})
    assert result["available"] is False
    assert result["decision_queue"].empty
