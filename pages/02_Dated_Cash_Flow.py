"""Standalone Streamlit page for dated project cash-flow forecasting."""
from __future__ import annotations

import json
import streamlit as st

from ai_project_control.dated_cashflow_forecast import build_dated_cashflow_forecast

st.set_page_config(page_title="Dated Cash Flow Forecast", page_icon="💧", layout="wide")
st.title("Dated Cash Flow Forecast")
st.caption("Pisahkan arus kas aktual dan rencana berdasarkan tanggal, proyek, dan mata uang.")

opening_default = """{
  "IDR": 1000000000,
  "USD": 25000
}"""
transactions_default = """[
  {
    "transaction_id": "TX-001",
    "date": "2026-12-01",
    "project_id": "PROJECT-001",
    "currency": "IDR",
    "direction": "OUTFLOW",
    "amount": 150000000,
    "status": "ACTUAL",
    "description": "Pembayaran aktual kontraktor"
  },
  {
    "transaction_id": "TX-002",
    "date": "2026-12-15",
    "project_id": "PROJECT-001",
    "currency": "IDR",
    "direction": "OUTFLOW",
    "amount": 300000000,
    "status": "FORECAST",
    "description": "Rencana pembayaran alat"
  },
  {
    "transaction_id": "TX-003",
    "date": "2026-12-20",
    "project_id": "PROJECT-001",
    "currency": "IDR",
    "direction": "INFLOW",
    "amount": 500000000,
    "status": "FORECAST",
    "description": "Rencana termin pembayaran"
  }
]"""

st.warning("Masukkan saldo awal yang sudah direkonsiliasi dan transaksi dari sumber resmi. Contoh bawaan hanya ilustrasi, bukan data aktual.")
with st.form("dated_cashflow_input"):
    opening_json = st.text_area("Opening cash by currency (JSON)", value=opening_default, height=110)
    transactions_json = st.text_area("Transactions (JSON)", value=transactions_default, height=300)
    submitted = st.form_submit_button("Build cash-flow forecast")

if submitted:
    try:
        opening = json.loads(opening_json)
        transactions = json.loads(transactions_json)
        result = build_dated_cashflow_forecast(transactions, opening)
        st.subheader("Forecast summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Transactions", result["transaction_count"])
        m2.metric("Actual", result["actual_transaction_count"])
        m3.metric("Forecast", result["forecast_transaction_count"])
        for currency, view in result["by_currency"].items():
            st.markdown(f"### {currency}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Opening balance", f"{view['opening_balance']:,.2f}")
            c2.metric("Projected closing balance", f"{view['closing_balance']:,.2f}")
            c3.metric("Minimum projected balance", f"{view['minimum_projected_balance']:,.2f}")
            if view["negative_balance_dates"]:
                st.error("Projected negative balance: " + ", ".join(view["negative_balance_dates"]))
            st.markdown("**Daily cash position**")
            st.dataframe(view["daily_timeline"], use_container_width=True, hide_index=True)
            st.markdown("**Monthly flow summary**")
            st.dataframe(view["monthly_summary"], use_container_width=True, hide_index=True)
        st.download_button(
            "Download forecast JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="dated_cashflow_forecast.json",
            mime="application/json",
        )
        with st.expander("Methodology and limitations"):
            for note in result["limitations"]:
                st.write("• " + note)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        st.error("Input tidak dapat diproses: " + str(exc))
