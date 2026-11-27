"""Standalone Streamlit page for dated project cash-flow forecasting."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from ai_project_control.dated_cashflow_forecast import build_dated_cashflow_forecast

st.set_page_config(page_title="Dated Cash Flow Forecast", page_icon="💧", layout="wide")
from ai_project_control.ui_theme import apply_project_control_theme
apply_project_control_theme(
    "Dated Cash Flow Forecast",
    "Treasury visibility • Actual vs planned movements • Project and currency exposure",
    "FINANCIAL CONTROL / CASH MANAGEMENT",
)
st.caption("Pantau posisi kas harian dan bulanan. Saldo awal harus direkonsiliasi; data contoh bukan data aktual.")

opening_default = pd.DataFrame([
    {"currency": "IDR", "opening_balance": 1000000000},
    {"currency": "USD", "opening_balance": 25000},
])
transactions_default = pd.DataFrame([
    {"transaction_id": "TX-001", "date": "2026-12-01", "project_id": "PROJECT-001",
     "currency": "IDR", "direction": "OUTFLOW", "amount": 150000000,
     "status": "ACTUAL", "description": "Pembayaran aktual kontraktor"},
    {"transaction_id": "TX-002", "date": "2026-12-15", "project_id": "PROJECT-001",
     "currency": "IDR", "direction": "OUTFLOW", "amount": 300000000,
     "status": "FORECAST", "description": "Rencana pembayaran alat"},
    {"transaction_id": "TX-003", "date": "2026-12-20", "project_id": "PROJECT-001",
     "currency": "IDR", "direction": "INFLOW", "amount": 500000000,
     "status": "FORECAST", "description": "Rencana termin pembayaran"},
])
transactions_default["date"] = pd.to_datetime(transactions_default["date"]).dt.date
st.info("CONTROL NOTE  |  Gunakan saldo awal yang sudah direkonsiliasi. Actual dan forecast dipisahkan; mata uang tidak dikonversi otomatis.")
with st.form("dated_cashflow_input"):
    st.markdown("### Opening cash by currency")
    opening_df = st.data_editor(
        opening_default, num_rows="dynamic", use_container_width=True,
        key="cashflow_opening_editor",
        column_config={
            "currency": st.column_config.TextColumn("Currency code"),
            "opening_balance": st.column_config.NumberColumn("Reconciled opening balance"),
        },
    )
    st.markdown("### Dated transaction register")
    st.caption("Tambahkan transaksi pada tabel. Gunakan ACTUAL untuk transaksi yang sudah terjadi dan FORECAST untuk rencana.")
    transactions_df = st.data_editor(
        transactions_default, num_rows="dynamic", use_container_width=True,
        key="cashflow_transaction_editor",
        column_config={
            "date": st.column_config.DateColumn("Transaction date"),
            "direction": st.column_config.SelectboxColumn("Flow", options=["INFLOW", "OUTFLOW"]),
            "status": st.column_config.SelectboxColumn("Record type", options=["ACTUAL", "FORECAST"]),
            "amount": st.column_config.NumberColumn("Amount", min_value=0.01, format="%.2f"),
        },
    )
    submitted = st.form_submit_button("Build cash-flow forecast")
if submitted:
    try:
        opening_rows = opening_df.where(pd.notna(opening_df), None).to_dict(orient="records")
        transaction_rows = transactions_df.where(pd.notna(transactions_df), None).to_dict(orient="records")
        opening = {
            str(row.get("currency", "")).strip(): row.get("opening_balance")
            for row in opening_rows if str(row.get("currency", "")).strip()
        }
        transactions = [
            {**row, "date": row["date"].isoformat() if hasattr(row.get("date"), "isoformat") else row.get("date")}
            for row in transaction_rows if row.get("transaction_id") not in (None, "")
        ]
        result = build_dated_cashflow_forecast(transactions, opening)
        st.subheader("Cash position overview")
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
            st.markdown("#### Project movement summary")
            project_view = pd.DataFrame(view["project_summary"])
            st.dataframe(project_view, use_container_width=True, hide_index=True)
            if not project_view.empty:
                chart_data = project_view.set_index("project_id")[["actual_net", "forecast_net"]]
                st.markdown("##### Net movement by project")
                st.bar_chart(chart_data, use_container_width=True)
            st.markdown("#### Daily cash position")
            daily_view = pd.DataFrame(view["daily_timeline"])
            st.dataframe(daily_view, use_container_width=True, hide_index=True)
            if not daily_view.empty:
                st.markdown("##### Projected closing cash balance")
                st.line_chart(daily_view.set_index("date")[["closing_balance"]], use_container_width=True)
            st.markdown("#### Monthly flow summary")
            st.dataframe(view["monthly_summary"], use_container_width=True, hide_index=True)
        st.caption("Project summary shows movements only. Opening cash is held at currency level and is not allocated to projects.")
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
