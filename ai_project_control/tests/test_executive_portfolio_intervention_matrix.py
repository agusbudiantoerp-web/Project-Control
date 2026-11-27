from pathlib import Path


def test_executive_portfolio_intervention_matrix_is_rendered():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Executive Portfolio Intervention Matrix" in source
    assert "recommended_management_action" in source
    assert "executive_portfolio_intervention_matrix.csv" in source
    assert '"P1 - Immediate"' in source
    assert "cost_variance_pct" in source
