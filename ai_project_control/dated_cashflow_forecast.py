"""Dated, currency-safe cash flow forecasting from explicit transactions."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any


def build_dated_cashflow_forecast(
    transactions: list[dict[str, Any]],
    opening_cash_by_currency: dict[str, float],
) -> dict[str, Any]:
    """Aggregate actual/forecast inflows and outflows without FX conversion.

    Each transaction requires transaction_id, date (YYYY-MM-DD), project_id,
    currency, direction (INFLOW/OUTFLOW), amount (>0), and status (ACTUAL/FORECAST).
    Opening balances are explicit per currency; forecast rows are not treated as
    actual cash movements.
    """
    if not isinstance(transactions, list) or any(not isinstance(row, dict) for row in transactions):
        raise TypeError("transactions must be a list of dictionaries")
    if not isinstance(opening_cash_by_currency, dict):
        raise TypeError("opening_cash_by_currency must be a dictionary")

    opening: dict[str, float] = {}
    for raw_currency, raw_amount in opening_cash_by_currency.items():
        currency = str(raw_currency).strip().upper()
        if not currency:
            raise ValueError("opening balance currency is required")
        amount = float(raw_amount)
        if not math.isfinite(amount):
            raise ValueError(f"opening cash must be finite for {currency}")
        if currency in opening:
            raise ValueError(f"duplicate normalized currency: {currency}")
        opening[currency] = amount

    normalized = []
    seen_ids: set[str] = set()
    for row in transactions:
        tx_id = str(row.get("transaction_id", "")).strip()
        project_id = str(row.get("project_id", "")).strip()
        currency = str(row.get("currency", "")).strip().upper()
        direction = str(row.get("direction", "")).strip().upper()
        status = str(row.get("status", "")).strip().upper()
        if not tx_id or not project_id or not currency:
            raise ValueError("transaction_id, project_id and currency are required")
        if tx_id in seen_ids:
            raise ValueError(f"duplicate transaction_id: {tx_id}")
        seen_ids.add(tx_id)
        try:
            day = date.fromisoformat(str(row.get("date", "")))
            amount = float(row.get("amount"))
        except (TypeError, ValueError):
            raise ValueError(f"invalid date or amount for transaction {tx_id}") from None
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError(f"amount must be finite and greater than zero for {tx_id}")
        if direction not in {"INFLOW", "OUTFLOW"}:
            raise ValueError(f"invalid direction for {tx_id}")
        if status not in {"ACTUAL", "FORECAST"}:
            raise ValueError(f"invalid status for {tx_id}")
        if currency not in opening:
            raise ValueError(f"opening cash is required for currency {currency}")
        signed = amount if direction == "INFLOW" else -amount
        normalized.append({
            "transaction_id": tx_id, "date": day.isoformat(), "project_id": project_id,
            "currency": currency, "direction": direction, "amount": round(amount, 2),
            "status": status, "signed_amount": signed,
            "description": str(row.get("description", "")),
        })

    normalized.sort(key=lambda item: (item["currency"], item["date"], item["transaction_id"]))
    daily: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"actual_inflow": 0.0, "actual_outflow": 0.0,
                 "forecast_inflow": 0.0, "forecast_outflow": 0.0}
    )
    monthly: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"actual_inflow": 0.0, "actual_outflow": 0.0,
                 "forecast_inflow": 0.0, "forecast_outflow": 0.0}
    )
    for item in normalized:
        bucket = "actual" if item["status"] == "ACTUAL" else "forecast"
        flow = "inflow" if item["direction"] == "INFLOW" else "outflow"
        key = f"{bucket}_{flow}"
        daily[(item["currency"], item["date"])][key] += item["amount"]
        monthly[(item["currency"], item["date"][:7])][key] += item["amount"]

    currency_views = {}
    for currency, opening_balance in sorted(opening.items()):
        balance = opening_balance
        timeline = []
        negative_dates = []
        currency_days = sorted(day for curr, day in daily if curr == currency)
        for day in currency_days:
            flows = daily[(currency, day)]
            actual_net = flows["actual_inflow"] - flows["actual_outflow"]
            forecast_net = flows["forecast_inflow"] - flows["forecast_outflow"]
            balance += actual_net + forecast_net
            row = {
                "date": day,
                **{key: round(value, 2) for key, value in flows.items()},
                "net_movement": round(actual_net + forecast_net, 2),
                "closing_balance": round(balance, 2),
            }
            timeline.append(row)
            if balance < 0:
                negative_dates.append(day)

        monthly_rows = []
        for (curr, period), values in sorted(monthly.items()):
            if curr != currency:
                continue
            monthly_rows.append({
                "period": period,
                **{key: round(value, 2) for key, value in values.items()},
                "net_movement": round(
                    values["actual_inflow"] + values["forecast_inflow"]
                    - values["actual_outflow"] - values["forecast_outflow"], 2
                ),
            })
        currency_views[currency] = {
            "opening_balance": round(opening_balance, 2),
            "closing_balance": round(balance, 2),
            "minimum_projected_balance": round(min(
                [opening_balance] + [row["closing_balance"] for row in timeline]
            ), 2),
            "negative_balance_dates": negative_dates,
            "daily_timeline": timeline,
            "monthly_summary": monthly_rows,
        }

    return {
        "status": "ASSESSED" if normalized or opening else "INSUFFICIENT_DATA",
        "transaction_count": len(normalized),
        "actual_transaction_count": sum(row["status"] == "ACTUAL" for row in normalized),
        "forecast_transaction_count": sum(row["status"] == "FORECAST" for row in normalized),
        "transactions": normalized,
        "by_currency": currency_views,
        "limitations": [
            "Forecast rows are user-supplied planned transactions; no payment-date prediction is inferred.",
            "Opening cash balances must be supplied and reconciled to a trusted bank or treasury source.",
            "Currencies are kept separate; no FX conversion, financing facility or intercompany netting is assumed.",
            "The closing balance is a modeled cash position, not a bank-confirmed balance.",
        ],
    }
