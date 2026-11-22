from pathlib import Path


def test_portfolio_cost_forecast_is_currency_scoped():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Portfolio Cost Forecast by Currency" in source
    assert 'groupby("currency"' in source
    assert "portfolio_cost_forecast_by_currency.csv" in source
    assert "forecast_variance_pct" in source
