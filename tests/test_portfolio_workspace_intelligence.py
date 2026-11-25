from ai_project_control.portfolio_workspace_intelligence import build_stored_portfolio_risk_resource_view
from ai_project_control.project_store import ProjectStore


def test_stored_portfolio_intelligence_reads_multiple_project_workspaces(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    store.save_dataset("P1", "project_master", [{"project_id": "P1", "project_name": "Mine A", "currency": "IDR"}])
    store.save_dataset("P1", "risk", [{"project_id": "P1", "risk_id": "R1", "probability": .5, "impact": 100}])
    store.save_dataset("P1", "resources", [{"project_id": "P1", "resource_id": "EX-01", "period": "2026-12", "unit": "hours", "planned_units": 70, "capacity_units": 100}])
    store.save_dataset("P2", "project_master", [{"project_id": "P2", "project_name": "Road B", "currency": "USD"}])
    store.save_dataset("P2", "risk", [{"project_id": "P2", "risk_id": "R2", "probability": .2, "impact": 100}])
    store.save_dataset("P2", "resources", [{"project_id": "P2", "resource_id": "EX-01", "period": "2026-12", "unit": "hours", "planned_units": 50, "capacity_units": 100}])

    result = build_stored_portfolio_risk_resource_view(db)
    assert result["project_count"] == 2
    assert result["expected_exposure_by_currency"] == {"IDR": 50.0, "USD": 20.0}
    assert result["shared_resource_conflict_count"] == 1
    assert result["shared_resource_conflicts"][0]["overload_units"] == 20
