"""Explicit Telegram delivery adapter for executive action escalations.

No message is sent at import time. Call send_telegram_message only from an
explicit user action. Credentials are read from environment variables.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def format_escalation_message(result: dict[str, Any]) -> str:
    """Format a compact Indonesian summary without exposing credentials."""
    rows = result.get("escalations", [])
    summary = result.get("summary", {})
    lines = [
        "PROJECT CONTROL — GOVERNANCE ESCALATION",
        f"Tanggal pemeriksaan: {result.get('as_of', 'Tidak tersedia')}",
        f"Total eskalasi: {summary.get('escalation_count', len(rows))}",
        f"Project Director: {summary.get('director_count', 0)} | "
        f"Project Manager: {summary.get('manager_count', 0)}",
    ]
    for row in rows[:20]:
        lines.extend([
            "",
            f"[{row.get('priority', 'N/A')}] {row.get('title') or row.get('action_id')}",
            f"Proyek: {row.get('project_id') or 'Tidak dicantumkan'}",
            f"Status: {row.get('status', 'N/A')} | Tenggat: {row.get('due_date') or 'Belum tersedia'}",
            f"Penanggung jawab: {row.get('owner') or 'Belum ditetapkan'}",
            f"Eskalasi: {row.get('escalation_level', 'N/A')} — {row.get('reason', 'N/A')}",
            f"Tindakan: {row.get('recommended_action', 'Tinjau secara manual')}",
        ])
    if len(rows) > 20:
        lines.append(f"\nCatatan: {len(rows) - 20} eskalasi lainnya tidak ditampilkan.")
    lines.append("\nPesan ini merupakan bahan tinjauan; bukan persetujuan atau perubahan status otomatis.")
    message = "\n".join(lines)
    if len(message) > 3900:
        message = message[:3870] + "\n… pesan dipotong agar sesuai batas Telegram."
    return message


def send_telegram_message(
    message: str, *, bot_token: str | None = None, chat_id: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Send one message to a configured Telegram chat; credentials are never returned."""
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    destination = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
    if not token.strip() or not destination.strip():
        raise ValueError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before sending.")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string.")
    if len(message) > 4096:
        raise ValueError("Telegram message exceeds 4096 characters.")

    payload = json.dumps({
        "chat_id": destination,
        "text": message,
        "disable_web_page_preview": True,
    }).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Telegram delivery failed; check network and bot configuration.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Telegram returned an unreadable response.") from exc
    if not data.get("ok"):
        description = str(data.get("description", "Telegram rejected the message"))
        raise RuntimeError(f"Telegram delivery rejected: {description}")
    return {"status": "SENT", "message_id": data.get("result", {}).get("message_id")}
