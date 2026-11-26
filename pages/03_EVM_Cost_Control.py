"""Streamlit page for integrated EVM and cost forecast review."""
import json
import streamlit as st

from ai_project_control.financial_control_brief import build_financial_control_brief

st.set_page_config(page_title="EVM & Cost Control", page_icon="📈", layout="wide")
from ai_project_control.ui_theme import apply_project_control_theme
apply_project_control_theme(
    "EVM & Cost Forecast Control",
    "Earned value performance • Cost efficiency • Estimate-at-completion scenarios",
    "PROJECT CONTROLS / PERFORMANCE & COST",
)
st.info("CONTROL NOTE  |  Contoh data hanya untuk demonstrasi. Gunakan progress terukur dan actual cost tervalidasi untuk keputusan proyek.")

project_default = {"project_id": "PROJECT-001", "BAC": 1000000000, "currency": "IDR"}
progress_default = [{"project_id": "PROJECT-001", "period": "2026-10", "planned_value": 500000000, "earned_value": 400000000}]
cost_default = [{"project_id": "PROJECT-001", "period": "2026-10", "actual_cost": 500000000}]
with st.form("evm_cost_control"):
    project_text = st.text_area("Project and BAC (JSON)", json.dumps(project_default, indent=2))
    progress_text = st.text_area("Progress records (JSON)", json.dumps(progress_default, indent=2))
    cost_text = st.text_area("Actual cost records (JSON)", json.dumps(cost_default, indent=2))
    period = st.text_input("As-of period (optional, e.g. 2026-10)")
    progress_mode_label = st.selectbox(
        "Progress record convention",
        ["Period movements (delta)", "Cumulative snapshots"],
        help="Choose period movements when each row contains only that period's value. Choose cumulative snapshots when rows repeat the cumulative-to-date value.",
    )
    cost_mode_label = st.selectbox(
        "Actual cost record convention",
        ["Period movements (delta)", "Cumulative snapshots"],
        help="Choose the convention used by your cost ledger export. Do not sum cumulative snapshots as period movements.",
    )
    threshold = st.number_input("Budget variance warning threshold (%)", min_value=0.0, value=5.0, step=0.5)
    submitted = st.form_submit_button("Calculate EVM and cost outlook")
if submitted:
    try:
        project = json.loads(project_text)
        progress = json.loads(progress_text)
        costs = json.loads(cost_text)
        if not isinstance(project, dict) or not isinstance(progress, list) or not isinstance(costs, list):
            raise TypeError("Project input must be an object; progress and cost inputs must be arrays.")
        result = build_financial_control_brief(
            project, progress, costs,
            as_of_period=period.strip() or None,
            warning_threshold_pct=threshold,
            progress_record_mode=("period_delta" if progress_mode_label.startswith("Period") else "cumulative_snapshot"),
            actual_cost_record_mode=("period_delta" if cost_mode_label.startswith("Period") else "cumulative_snapshot"),
        )
        st.subheader("Performance and cost position")
        evm = result["evm"]
        st.caption(f"Project: {result['project_id']}  |  Currency: {result['currency'] or 'Not specified'}  |  As-of: {result['as_of_period'] or 'Latest available'}")
        cols = st.columns(4)
        for col, key in zip(cols, ("PV", "EV", "AC", "BAC")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        cols = st.columns(4)
        for col, key in zip(cols, ("SV", "CV", "SPI", "CPI")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        cols = st.columns(4)
        for col, key in zip(cols, ("EAC", "ETC", "VAC", "TCPI")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        st.caption(
            f"Source records used — progress: {evm['source_record_counts']['progress']}, "
            f"actual cost: {evm['source_record_counts']['actual_cost']}"
        )
        if evm.get("data_gaps"):
            st.warning("EVM data gaps: " + ", ".join(evm["data_gaps"]))
        if result["status"] != "ASSESSED":
            st.warning("Review required: one or more required source values are missing or invalid.")
        if result["management_alerts"]:
            st.markdown("### Management attention")
            for alert in result["management_alerts"]:
                st.write(f"**{alert['severity']} — {alert['code']}**: {alert['message']}")
        else:
            st.success("No threshold alerts were generated from the submitted data.")
        st.markdown("### Estimate at Completion — scenario comparison")
        st.dataframe(result["cost_forecast"].get("scenarios", []), use_container_width=True, hide_index=True)
        st.download_button("Download financial control JSON",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="financial_control_brief.json", mime="application/json")
        with st.expander("Methodology and guardrails"):
            st.json({"EVM": evm.get("method"), "limitations": evm.get("limitations"),
                     "forecast_limitations": result["cost_forecast"].get("limitations"),
                     "decision_guardrails": result["decision_guardrails"]})
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        st.error("Input tidak dapat diproses: " + str(exc))
