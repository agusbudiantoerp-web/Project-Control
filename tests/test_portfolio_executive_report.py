"""Regression tests for bilingual portfolio executive reporting."""
from ai_project_control.portfolio_executive_report import build_portfolio_executive_report


def test_indonesian_report_contains_portfolio_counts_and_currency():
    report = build_portfolio_executive_report([
        {"project_id": "P1", "project_name": "Project One", "SPI": 0.8, "CPI": 0.9,
         "budget_at_completion": 1000, "currency": "IDR"},
        {"project_id": "P2", "SPI": None, "CPI": 1.0},
    ], "2026-11-23", "id")
    assert "LAPORAN EKSEKUTIF KINERJA PORTOFOLIO" in report
    assert "Insufficient data: 1" in report
    assert "IDR: 1,000.00" in report
    assert "INSUFFICIENT_DATA" in report


def test_english_report_is_bilingual_option_and_handles_empty_portfolio():
    report = build_portfolio_executive_report([], "2026-11-23", "en")
    assert "EXECUTIVE PORTFOLIO PERFORMANCE REPORT" in report
    assert "Projects: 0" in report
    assert "Not available" in report


def test_report_does_not_mix_currency_totals():
    report = build_portfolio_executive_report([
        {"project_id": "A", "SPI": 1, "CPI": 1, "budget_at_completion": 100, "currency": "IDR"},
        {"project_id": "B", "SPI": 1, "CPI": 1, "budget_at_completion": 10, "currency": "USD"},
    ], "2026-11-23")
    assert "IDR: 100.00" in report
    assert "USD: 10.00" in report
    assert "110.00" not in report
