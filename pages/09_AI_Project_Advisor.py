"""Evidence-grounded Groq/Gemini project advisor for the saved primary workspace."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from ai_project_control.action_register_store import ActionRegisterStore
from ai_project_control.ai_narrative_advisor import generate_narrative_advice
from ai_project_control.project_store import ProjectStore
from ai_project_control.workspace_config import get_workspace_database_path
from ai_project_control.workspace_service import build_workspace_overview

st.set_page_config(page_title="AI Project Advisor", page_icon="🤖", layout="wide")
apply_project_control_theme("AI Project Advisor", "Evidence-grounded management insights with human review and controlled decision boundaries.", "AI DECISION SUPPORT / HUMAN GOVERNANCE")
st.title("AI Project Advisor — Groq / Gemini")
st.caption(
    "Analisis manajemen berbasis data proyek tersimpan. AI hanya memberi narasi dan rekomendasi; "
    "tidak mengubah jadwal, baseline, biaya, atau status tindakan."
)

database_path = get_workspace_database_path()
try:
    store = ProjectStore(database_path)
    project_ids = store.list_project_ids()
except (OSError, RuntimeError, ValueError) as exc:
    st.error("Project workspace tidak tersedia: " + str(exc))
    st.stop()

if not project_ids:
    st.info("Belum ada Project Master. Impor proyek terlebih dahulu melalui Project Workspace.")
    st.stop()

project_id = st.selectbox("Pilih proyek", project_ids, key="pc_ai_advisor_project")
try:
    overview = build_workspace_overview(database_path, project_id)
    project = overview["project"]
    evm = overview["evm"]
    schedule = overview["schedule"]
    forecast = overview["schedule_forecast"]
    risk_rows = overview["workspace"].get("risk", [])
    resource_rows = overview["workspace"].get("resources", [])
    action_register = ActionRegisterStore(database_path).list_project(project_id)
except (OSError, RuntimeError, ValueError, TypeError) as exc:
    st.error("Data proyek belum dapat dianalisis: " + str(exc))
    st.stop()

metrics = {
    "project_id": project_id,
    "project_name": project.get("project_name", project_id),
    "currency": project.get("currency"),
    "EVM": {key: evm.get(key) for key in ("PV", "EV", "AC", "BAC", "SV", "CV", "SPI", "CPI", "EAC", "ETC", "VAC", "TCPI")},
    "EVM_status": evm.get("status"),
    "EVM_data_gaps": evm.get("data_gaps", []),
    "schedule_status": schedule.get("status"),
    "activity_count": schedule.get("activity_count", len(overview["workspace"].get("activities", []))),
    "critical_activity_count": sum(
        1 for row in schedule.get("activities", []) if row.get("is_critical")
    ),
    "schedule_forecast_status": forecast.get("status"),
    "delayed_activity_ids": forecast.get("delayed_activity_ids", []),
    "unassessed_activity_ids": forecast.get("unassessed_activity_ids", []),
    "risk_record_count": len(risk_rows),
    "resource_record_count": len(resource_rows),
    "open_actions": action_register.get("summary", {}).get("open_count", 0),
    "blocked_actions": action_register.get("summary", {}).get("blocked_count", 0),
    "overdue_actions": action_register.get("summary", {}).get("overdue_count", 0),
}
findings = pd.DataFrame(risk_rows)
if not findings.empty:
    keep = [
        column for column in (
            "risk_id", "description", "risk_type", "probability", "impact",
            "risk_score", "cost_impact_min", "cost_impact_most_likely",
            "cost_impact_max", "currency", "activity_id", "wbs_id",
        ) if column in findings.columns
    ]
    findings = findings[keep].head(30)
actions = pd.DataFrame(action_register.get("actions", []))
if not actions.empty:
    keep = [
        column for column in (
            "action_id", "title", "description", "status", "priority",
            "owner", "due_date", "risk_id",
        ) if column in actions.columns
    ]
    actions = actions[keep].head(30)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Project", project.get("project_name") or project_id)
c2.metric("EVM status", evm.get("status", "Not assessed"))
c3.metric("Critical activities", metrics["critical_activity_count"])
c4.metric("Overdue actions", metrics["overdue_actions"])
with st.expander("Evidence sent to the AI provider", expanded=True):
    st.json(metrics)
    st.markdown("**Risk register evidence**")
    if findings.empty:
        st.info("Tidak ada baris risiko tersimpan. Ini bukan bukti bahwa proyek bebas risiko.")
    else:
        st.dataframe(findings, use_container_width=True, hide_index=True)
    st.markdown("**Executive action evidence**")
    if actions.empty:
        st.info("Belum ada tindakan tersimpan.")
    else:
        st.dataframe(actions, use_container_width=True, hide_index=True)

provider = st.selectbox("AI provider", ["Groq", "Gemini"], key="pc_ai_advisor_provider")
default_model = "llama-3.3-70b-versatile" if provider == "Groq" else "gemini-2.5-flash"
model = st.text_input("Model", value=default_model, key=f"pc_ai_advisor_model_{provider}")
timeout = st.number_input("Request timeout (seconds)", min_value=5, max_value=180, value=45, step=5)
consent = st.checkbox(
    f"Saya menyetujui metrik proyek, data risiko, dan tindakan yang ditampilkan dikirim ke {provider} untuk dianalisis.",
    key=f"pc_ai_advisor_consent_{provider}_{project_id}",
)
st.caption("API key dibaca dari environment atau Streamlit secrets. Kunci tidak ditampilkan dan tidak disimpan di ProjectStore.")
if st.button("Generate AI project analysis", type="primary", disabled=not consent):
    key_name = "GROQ_API_KEY" if provider == "Groq" else "GEMINI_API_KEY"
    api_key = os.getenv(key_name, "")
    if not api_key:
        try:
            api_key = str(st.secrets.get(key_name, ""))
        except Exception:
            api_key = ""
    if not api_key:
        st.error(f"{key_name} belum dikonfigurasi.")
    else:
        with st.spinner(f"Mengirim evidence terpilih ke {provider}..."):
            result = generate_narrative_advice(
                metrics,
                findings=findings,
                action_plan=actions,
                provider=provider,
                groq_api_key=api_key if provider == "Groq" else None,
                gemini_api_key=api_key if provider == "Gemini" else None,
                groq_model=model if provider == "Groq" else default_model,
                gemini_model=model if provider == "Gemini" else default_model,
                timeout=float(timeout),
            )
        if result.get("ok"):
            st.session_state[f"pc_ai_advisor_result_{project_id}"] = result
        else:
            st.error(result.get("error", "AI analysis failed. Check provider settings and connectivity."))

saved_result = st.session_state.get(f"pc_ai_advisor_result_{project_id}")
if saved_result:
    st.divider()
    st.markdown(f"### Analysis from {saved_result.get('provider')} · {saved_result.get('model')}")
    st.markdown(saved_result.get("text", ""))
    st.download_button(
        "Download AI project advice",
        data=saved_result.get("text", "").encode("utf-8"),
        file_name=f"AI_Project_Advice_{project_id}.md",
        mime="text/markdown",
    )
    st.caption("Analisis adalah bahan tinjauan. Verifikasi setiap fakta dan hipotesis dengan tim proyek sebelum mengambil tindakan.")\nfrom ai_project_control.ui_theme import apply_project_control_theme\napply_project_control_theme("AI Project Advisor", "Evidence-grounded management insights with human review and controlled decision boundaries.", "AI DECISION SUPPORT / HUMAN GOVERNANCE")
