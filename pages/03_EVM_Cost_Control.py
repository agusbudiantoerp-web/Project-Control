"""Streamlit page for integrated EVM and cost forecast review."""
import json
import streamlit as st

from ai_project_control.financial_control_brief import build_financial_control_brief

st.set_page_config(page_title="EVM & Cost Control", page_icon="📈", layout="wide")
st.title("EVM & Cost Forecast Control")
st.caption("PV, EV, AC, BAC, SPI, CPI and transparent Estimate-at-Completion scenarios.")
st.warning("Input contoh adalah ilustrasi. Gunakan data progress dan actual cost yang tervalidasi sebelum mengambil keputusan.")

project_default = {"project_id": "PROJECT-001", "BAC": 1000000000, "currency": "IDR"}
progress_default = [{"project_id": "PROJECT-001", "period": "2026-10", "planned_value": 500000000, "earned_value": 400000000}]
cost_default = [{"project_id": "PROJECT-001", "period": "2026-10", "actual_cost": 500000000}]
with st.form("evm_cost_control"):
    project_text = st.text_area("Project and BAC (JSON)", json.dumps(project_default, indent=2))
    progress_text = st.text_area("Progress records (JSON)", json.dumps(progress_default, indent=2))
    cost_text = st.text_area("Actual cost records (JSON)", json.dumps(cost_default, indent=2))
    period = st.text_input("As-of period (optional, e.g. 2026-10)")
    threshold = st.number_input("Budget variance warning threshold (%)", min_value=0.0, value=5.0, step=0.5)
    submitted = st.form_submit_button("Calculate EVM and cost outlook")
if submitted:
    try:
        project = json.loads(project_text)
        progress = json.loads(progress_text)
        costs = json.loads(cost_text)
        result = build_financial_control_brief(project, progress, costs,
            as_of_period=period.strip() or None, warning_threshold_pct=threshold)
        st.subheader("Executive financial indicators")
        evm = result["evm"]
        cols = st.columns(4)
        for col, key in zip(cols, ("SPI", "CPI", "EAC", "VAC")):
            value = evm.get(key)
            col.metric(key, "Not assessed" if value is None else f"{value:,.2f}")
        if result["status"] != "ASSESSED":
            st.warning("Review required: one or more required source values are missing or invalid.")
        for alert in result["management_alerts"]:
            st.write(f"**{alert['severity']} — {alert['code']}**: {alert['message']}")
        st.markdown("### EAC scenarios")
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
