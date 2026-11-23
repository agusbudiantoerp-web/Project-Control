"""Telegram executive text reporting with explicit-send and credential safeguards."""
from __future__ import annotations

from typing import Any, Iterable

TELEGRAM_TEXT_LIMIT = 4000


def build_telegram_executive_message(
    *,
    project_name: str,
    status_date: Any,
    intelligence: dict[str, Any] | None = None,
    action_register: dict[str, Any] | None = None,
) -> str:
    """Create a compact factual status message from supplied records only."""
    title = str(project_name or "").strip() or "Unnamed project"
    day = str(status_date or "").strip()
    lines = [f"AI PROJECT CONTROL | {title}", f"Status date: {day}"]
    summary = (intelligence or {}).get("summary", {})
    if summary:
        lines.extend([
            "",
            "PORTFOLIO INTELLIGENCE",
            f"Projects: {summary.get('project_count', 0)}",
            f"P1 immediate review: {summary.get('p1_count', 0)}",
            f"P2 recovery review: {summary.get('p2_count', 0)}",
            f"Critical risk: {summary.get('critical_risk_count', 0)}",
            f"High risk: {summary.get('high_risk_count', 0)}",
            f"Performance data incomplete: {summary.get('insufficient_performance_data_count', 0)}",
        ])
    actions = (action_register or {}).get("summary", {})
    if actions:
        lines.extend([
            "",
            "EXECUTIVE ACTIONS",
            f"Open: {actions.get('open_count', 0)} | In progress: {actions.get('in_progress_count', 0)}",
            f"Blocked: {actions.get('blocked_count', 0)} | Overdue: {actions.get('overdue_count', 0)}",
        ])
    lines.extend([
        "",
        "Screening information only. Verify source records and obtain authorized review before decisions.",
    ])
    return "\n".join(lines)


def split_telegram_message(message: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Split text into Telegram-safe chunks without dropping characters."""
    if limit < 100:
        raise ValueError("limit must be at least 100 characters")
    text = str(message)
    if not text:
        return []
    chunks = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def send_telegram_executive_message(
    *,
    bot_token: str,
    chat_id: str,
    message: str,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Send a message only when explicitly invoked by the host application."""
    import requests

    token = str(bot_token or "").strip()
    target = str(chat_id or "").strip()
    if not token:
        raise ValueError("Telegram bot token is not configured")
    if not target:
        raise ValueError("Telegram chat ID is not configured")
    chunks = split_telegram_message(message)
    if not chunks:
        raise ValueError("Telegram message is empty")
    results = []
    for chunk in chunks:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": target, "text": chunk, "disable_web_page_preview": True},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", "Telegram API rejected the message"))
        results.append(payload)
    return results
