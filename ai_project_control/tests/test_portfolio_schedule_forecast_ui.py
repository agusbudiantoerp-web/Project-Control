from pathlib import Path


def test_portfolio_schedule_forecast_fields_are_exposed():
    source = (Path(__file__).resolve().parents[1] / "core.py").read_text(encoding="utf-8")
    assert '"baseline_finish"' in source
    assert '"forecast_finish"' in source
    assert '"schedule_slip_days"' in source
    assert "planned_start + (baseline_finish - planned_start) / row[\"SPI\"]" in source


def test_portfolio_schedule_forecast_is_rendered_and_exportable():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Portfolio Schedule Forecast" in source
    assert "portfolio_schedule_forecast.csv" in source
    assert "Forecast delay" in source
