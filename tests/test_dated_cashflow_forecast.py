import pytest

from ai_project_control.dated_cashflow_forecast import build_dated_cashflow_forecast


def test_cashflow_separates_actual_and_forecast_and_tracks_running_balance():
    result = build_dated_cashflow_forecast(
        [
            {"transaction_id": "T1", "date": "2026-12-01", "project_id": "P1",
             "currency": "IDR", "direction": "INFLOW", "amount": 100, "status": "ACTUAL"},
            {"transaction_id": "T2", "date": "2026-12-02", "project_id": "P1",
             "currency": "IDR", "direction": "OUTFLOW", "amount": 130, "status": "FORECAST"},
        ],
        {"IDR": 50},
    )
    view = result["by_currency"]["IDR"]
    assert result["actual_transaction_count"] == 1
    assert result["forecast_transaction_count"] == 1
    assert view["daily_timeline"][-1]["closing_balance"] == 20
    assert view["negative_balance_dates"] == []


def test_negative_projected_cash_is_flagged():
    result = build_dated_cashflow_forecast(
        [{"transaction_id": "T1", "date": "2026-12-01", "project_id": "P1",
          "currency": "USD", "direction": "OUTFLOW", "amount": 150, "status": "FORECAST"}],
        {"USD": 100},
    )
    assert result["by_currency"]["USD"]["negative_balance_dates"] == ["2026-12-01"]
    assert result["by_currency"]["USD"]["minimum_projected_balance"] == -50


def test_currencies_are_not_combined():
    result = build_dated_cashflow_forecast([], {"IDR": 100, "USD": 20})
    assert set(result["by_currency"]) == {"IDR", "USD"}


@pytest.mark.parametrize("bad_amount", [0, -1, float("inf"), float("nan")])
def test_invalid_amount_rejected(bad_amount):
    with pytest.raises(ValueError, match="amount"):
        build_dated_cashflow_forecast(
            [{"transaction_id": "T1", "date": "2026-12-01", "project_id": "P1",
              "currency": "IDR", "direction": "OUTFLOW", "amount": bad_amount, "status": "ACTUAL"}],
            {"IDR": 100},
        )


def test_duplicate_ids_and_missing_opening_currency_rejected():
    row = {"transaction_id": "T1", "date": "2026-12-01", "project_id": "P1",
           "currency": "IDR", "direction": "OUTFLOW", "amount": 10, "status": "ACTUAL"}
    with pytest.raises(ValueError, match="duplicate"):
        build_dated_cashflow_forecast([row, row], {"IDR": 100})
    with pytest.raises(ValueError, match="opening cash"):
        build_dated_cashflow_forecast([row], {"USD": 100})
