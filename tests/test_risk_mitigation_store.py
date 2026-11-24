import pytest

from ai_project_control.risk_mitigation_store import RiskMitigationStore


def test_mitigation_create_update_and_project_isolation(tmp_path):
    store = RiskMitigationStore(tmp_path / "workspace.sqlite3")
    first = store.save(
        project_id="P-01", risk_id="R-01",
        mitigation_action="Secure alternate supplier",
        owner="Procurement Lead", due_date="2026-12-01",
        status="IN_PROGRESS", residual_probability=.25,
        residual_impact=100, evidence="Vendor quotation pending",
        updated_by="Project Manager",
    )
    assert first["residual_exposure"] == 25
    assert len(store.list_project("P-01")) == 1
    assert store.list_project("P-02") == []

    updated = store.save(
        project_id="P-01", risk_id="R-01",
        mitigation_action="Approve alternate supplier",
        owner="Procurement Lead", due_date="2026-12-03",
        status="VERIFIED", residual_probability=.1,
        residual_impact=80, evidence="Approval reference PO-123",
        updated_by="Project Director",
    )
    rows = store.list_project("P-01")
    assert len(rows) == 1
    assert rows[0]["status"] == "VERIFIED"
    assert rows[0]["residual_exposure"] == 8
    assert rows[0]["evidence"] == "Approval reference PO-123"


@pytest.mark.parametrize("probability", [-.1, 1.1, float("nan"), float("inf")])
def test_residual_probability_must_be_finite_and_between_zero_and_one(tmp_path, probability):
    store = RiskMitigationStore(tmp_path / "workspace.sqlite3")
    with pytest.raises(ValueError, match="residual_probability"):
        store.save(
            project_id="P", risk_id="R", mitigation_action="Act",
            owner="Owner", due_date="2026-12-01", status="PLANNED",
            residual_probability=probability, residual_impact=10, updated_by="User",
        )


def test_invalid_status_date_and_missing_fields_are_rejected(tmp_path):
    store = RiskMitigationStore(tmp_path / "workspace.sqlite3")
    common = dict(
        project_id="P", risk_id="R", mitigation_action="Act",
        owner="Owner", due_date="2026-12-01", status="PLANNED",
        residual_probability=.2, residual_impact=10, updated_by="User",
    )
    with pytest.raises(ValueError, match="status"):
        store.save(**{**common, "status": "DONE"})
    with pytest.raises(ValueError, match="due_date"):
        store.save(**{**common, "due_date": "not-a-date"})
    with pytest.raises(ValueError, match="owner"):
        store.save(**{**common, "owner": ""})


def test_in_memory_database_supported():
    store = RiskMitigationStore(":memory:")
    store.save(
        project_id="P", risk_id="R", mitigation_action="Act",
        owner="Owner", due_date="2026-12-01", status="PLANNED",
        residual_probability=.2, residual_impact=10, updated_by="User",
    )
    assert len(store.list_project("P")) == 1
