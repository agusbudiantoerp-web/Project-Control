from pathlib import Path


def test_portfolio_report_exports_excel_and_pdf():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Generate Portfolio Excel & PDF Pack" in source
    assert 'pd.ExcelWriter(excel_buffer, engine="openpyxl")' in source
    assert "SimpleDocTemplate" in source
    assert "AI_Project_Control_Portfolio_Report.xlsx" in source
    assert "AI_Project_Control_Portfolio_Report.pdf" in source


def test_portfolio_report_contains_core_management_sheets():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    for sheet in ("Portfolio KPI", "Risk Register", "Cost Forecast", "Intervention Matrix"):
        assert f'sheet_name="{sheet}"' in source
