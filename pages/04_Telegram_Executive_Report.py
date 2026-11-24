"""Explicit Telegram executive report composer and sender."""
from __future__ import annotations

import json
import os
import streamlit as st

from ai_project_control.telegram_executive_reporting import (
    build_telegram_executive_message,
    send_telegram_executive_message,
)

st.set_page_config(page_title="Telegram Executive Report", page_icon="✈️", layout="wide")
st.title("Telegram Executive Report")
st.caption("Compose a factual executive summary and send only after an explicit user action.")
st.warning("Telegram delivery requires a bot token and chat ID configured in Streamlit secrets or environment variables. Never paste credentials into this form.")

with st.form("telegram_report_compose"):
    project_name = st.text_input("Project / portfolio name", value="Project Portfolio")
    status_date = st.text_input("Reporting date", value="")
    intelligence_text = st.text_area("Portfolio intelligence JSON (optional)", value="{}")
    actions_text = st.text_area("Executive action register JSON (optional)", value="{}")
    compose = st.form_submit_button("Generate message")

if compose:
    try:
        intelligence = json.loads(intelligence_text)
        actions = json.loads(actions_text)
        if not isinstance(intelligence, dict) or not isinstance(actions, dict):
            raise ValueError("Both JSON inputs must be objects.")
        message = build_telegram_executive_message(
            project_name=project_name, status_date=status_date,
            intelligence=intelligence, action_register=actions,
        )
        st.session_state["telegram_executive_message"] = message
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        st.error("Input tidak valid: " + str(exc))

message = st.session_state.get("telegram_executive_message", "")
if message:
    st.subheader("Message preview")
    st.code(message)
    st.download_button("Download message text", data=message,
        file_name="telegram_executive_report.txt", mime="text/plain")
    st.divider()
    st.subheader("Explicit delivery")
    st.caption("Sending is a real external action. Check the destination and message before confirming.")
    confirmed = st.checkbox("I have reviewed this message and authorize sending it to the configured Telegram chat.")
    if st.button("Send Telegram report", type="primary", disabled=not confirmed):
        try:
            try:
                secrets = st.secrets
            except Exception:
                secrets = {}
            token = secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
            chat_id = secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))
            result = send_telegram_executive_message(
                bot_token=token, chat_id=chat_id, message=message,
            )
            st.success(f"Telegram accepted {len(result)} message part(s).")
        except Exception:
            st.error("Telegram delivery failed. Check the configured credentials, chat permissions, network connectivity and server logs. Credentials are intentionally not displayed.")
