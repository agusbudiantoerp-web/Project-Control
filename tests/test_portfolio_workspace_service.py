from ai_project_control.portfolio_workspace_service import build_saved_portfolio_report
from ai_project_control.project_store import ProjectStore


def add_project(store, project_id, name, pv, ev, ac, currency="IDR"):
    store.save_dataset(project_id, "project_master", [{
        "project_id": project_id, "project_name": name, "currency": currency, "BAC": 1000,
    }])
    if pv is not None:
        store.save_dataset(project_id, "progress", [{
            "project_id": project_id, "activity_id": "A1", "period": "2026-10",
            "planned_value": pv, "earned_value": ev,
        }])
    if ac is not None:
        store.save_dataset(project_id, "actual_cost", [{
            "project_id": project_id, "period": "2026-10",
            "cost_code": "C1", "actual_cost": ac,
        }])


def test_saved_portfolio_discovers_projects_and_scores_them(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    add_project(store, "P2", "Project Two", 500, 500, 400)
    result = build_saved_portfolio_report(db, as_of_period="2026-10")
    assert result["project_count"] == 2
    assert result["scorecard"]["summary"]["assessed_count"] == 2
    assert result["scorecard"]["summary"]["budget_by_currency"] == {"IDR": 2000}
    assert "Project One" in result["executive_report"]


def test_saved_portfolio_marks_missing_data_unassessed(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", None, None, None)
    result = build_saved_portfolio_report(db)
    assert result["scorecard"]["summary"]["insufficient_data_count"] == 1
    assert result["scorecard"]["projects"][0]["status"] == "INSUFFICIENT_DATA"


def test_saved_portfolio_does_not_combine_currencies(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project IDR", 500, 400, 500, "IDR")
    add_project(store, "P2", "Project USD", 500, 450, 450, "USD")
    result = build_saved_portfolio_report(db)
    assert result["scorecard"]["summary"]["budget_by_currency"] == {"IDR": 1000, "USD": 1000}


def test_saved_portfolio_empty_workspace_is_valid_empty_result(tmp_path):
    result = build_saved_portfolio_report(tmp_path / "empty.sqlite3")
    assert result["project_count"] == 0
    assert result["scorecard"]["summary"]["project_count"] == 0


def test_saved_portfolio_integrates_risk_governance_and_exposure(tmp_path):
    from ai_project_control.action_register_store import ActionRegisterStore
    from ai_project_control.risk_mitigation_store import RiskMitigationStore

    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    store.save_dataset("P1", "risk", [{
        "project_id": "P1", "risk_id": "R1", "description": "Critical path equipment delay",
        "probability": 0.8, "impact": 10, "activity_id": "A1", "wbs_id": "W1",
        "category": "SCHEDULE",
    }])
    store.save_dataset("P1", "activities", [{
        "project_id": "P1", "activity_id": "A1", "duration_days": 5, "predecessors": [],
    }])
    store.save_dataset("P1", "wbs", [{
        "project_id": "P1", "wbs_id": "W1", "wbs_name": "Construction",
    }])
    actions = ActionRegisterStore(db)
    actions.create(title="Expedite equipment", owner="Procurement", due_date="2026-11-01",
                   project_id="P1", created_by="PM", risk_id="R1", priority="P1")
    mitigations = RiskMitigationStore(db)
    mitigations.save(project_id="P1", risk_id="R1", mitigation_action="Expedite vendor",
                     owner="Procurement", due_date="2026-11-30", status="IN_PROGRESS",
                     residual_probability=0.4, residual_impact=5, updated_by="PM")
    result = build_saved_portfolio_report(db, as_of_date="2026-11-24")
    assert result["risk_governance_summary"]["risk_count"] == 1
    assert result["risk_governance_summary"]["risks_requiring_attention"] == 1
    assert result["risk_governance"][0]["rows"][0]["linked_action_count"] == 1
    assert result["risk_exposure_matrices"][0]["risks"][0]["priority"] == "CRITICAL"
    assert "Risk governance" in result["executive_report"]


def test_saved_portfolio_risk_matrix_marks_empty_risk_register(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    result = build_saved_portfolio_report(db)
    assert result["risk_governance"][0]["status"] == "NO_RISKS"
    assert result["risk_exposure_matrices"][0]["status"] == "NO_RISKS"


def test_saved_portfolio_uses_explicit_dated_health_snapshots(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    store.save_dataset("P1", "portfolio_snapshots", [
        {"project_id": "P1", "snapshot_date": "2026-11-01",
         "SPI": 1.0, "CPI": 1.0, "risk_score": 20},
        {"project_id": "P1", "snapshot_date": "2026-11-15",
         "SPI": 0.90, "CPI": 0.98, "risk_score": 32},
    ])
    result = build_saved_portfolio_report(db)
    trend = result["health_monitoring"]
    assert trend["summary"]["trend_assessed_count"] == 1
    assert trend["projects"][0]["changes"] == {
        "SPI": -0.1, "CPI": -0.02, "risk_score": 12.0,
    }
    assert "Portfolio health trends" in result["executive_report"]


def test_saved_portfolio_does_not_invent_health_baseline(tmp_path):
    db = tmp_path / "portfolio.sqlite3"
    store = ProjectStore(db)
    add_project(store, "P1", "Project One", 500, 400, 500)
    store.save_dataset("P1", "portfolio_snapshots", [{
        "project_id": "P1", "snapshot_date": "2026-11-15",
        "SPI": 0.9, "CPI": 0.95,
    }])
    result = build_saved_portfolio_report(db)
    assert result["health_monitoring"]["projects"][0]["status"] == "NO_BASELINE"
