from pathlib import Path


def test_portfolio_ai_advisor_uses_explicit_provider_opt_in():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "AI Portfolio Advisor — Groq / Gemini" in source
    assert 'st.button("Generate AI portfolio analysis"' in source
    assert "generate_narrative_advice(" in source
    assert "GROQ_API_KEY" in source
    assert "GEMINI_API_KEY" in source


def test_portfolio_ai_context_handles_missing_cost_forecast():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert '"cost_forecast_by_currency": currency_summary.to_dict("records") if "currency_summary" in locals()' in source
    assert '"delayed_forecast_projects": int((schedule_summary["schedule_slip_days"] > 0).sum()) if "schedule_summary" in locals()' in source
