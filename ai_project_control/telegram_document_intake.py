"""Explicit Telegram PDF intake for the primary drawing-to-BOQ workflow."""
from __future__ import annotations

import math
from typing import Any

import requests

MAX_TELEGRAM_PDF_BYTES = 20 * 1024 * 1024


def fetch_latest_telegram_pdf(
    bot_token: str,
    chat_id: str,
    *,
    offset: int | None = None,
    timeout: float = 20,
    max_bytes: int = MAX_TELEGRAM_PDF_BYTES,
) -> dict[str, Any] | None:
    """Fetch the newest PDF document from one authorized chat on explicit request.

    The update offset is returned to the caller for session persistence. Raw PDF
    bytes are returned to the caller and are not written to the project database.
    """
    if not isinstance(bot_token, str) or not bot_token.strip():
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    token = bot_token.strip()
    if any(character.isspace() for character in token):
        raise ValueError("TELEGRAM_BOT_TOKEN contains invalid whitespace")
    if not isinstance(chat_id, str) or not chat_id.strip():
        raise ValueError("TELEGRAM_CHAT_ID is required")
    destination = chat_id.strip()
    if offset is not None and (
        isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
    ):
        raise ValueError("Telegram update offset must be a non-negative integer")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite positive number")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if max_bytes > MAX_TELEGRAM_PDF_BYTES:
        raise ValueError("max_bytes cannot exceed the 20 MB Telegram PDF intake limit")

    base = f"https://api.telegram.org/bot{token}"
    params: dict[str, Any] = {"timeout": 0, "allowed_updates": '["message"]'}
    if offset is not None:
        params["offset"] = offset
    try:
        updates_response = requests.get(
            f"{base}/getUpdates", params=params, timeout=float(timeout)
        )
        updates_response.raise_for_status()
        payload = updates_response.json()
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise RuntimeError("Telegram getUpdates returned an unsuccessful response")
        updates = payload.get("result")
        if not isinstance(updates, list):
            raise RuntimeError("Telegram getUpdates response is malformed")
    except (requests.RequestException, ValueError, TypeError, RuntimeError):
        raise RuntimeError("Telegram document intake failed; check bot configuration and polling access.") from None

    next_offset = offset
    candidates = []
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int) and not isinstance(update_id, bool):
            next_offset = max(next_offset or 0, update_id + 1)
        message = update.get("message")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        if str(chat.get("id", "")).strip() != destination:
            continue
        document = message.get("document")
        if not isinstance(document, dict):
            continue
        file_name = str(document.get("file_name", "")).strip()
        mime_type = str(document.get("mime_type", "")).strip().lower()
        if not file_name.lower().endswith(".pdf") and mime_type != "application/pdf":
            continue
        file_size = document.get("file_size")
        if file_size is not None:
            if isinstance(file_size, bool) or not isinstance(file_size, int) or file_size < 0:
                continue
            if file_size > max_bytes:
                continue
        file_id = document.get("file_id")
        if not isinstance(file_id, str) or not file_id:
            continue
        candidates.append({
            "update_id": update_id,
            "file_id": file_id,
            "file_name": file_name or "telegram_drawing.pdf",
            "caption": str(message.get("caption", "")),
        })

    if not candidates:
        return {"status": "NO_PDF", "next_offset": next_offset}
    selected = max(
        candidates,
        key=lambda item: item["update_id"] if isinstance(item["update_id"], int) else -1,
    )
    try:
        file_response = requests.get(
            f"{base}/getFile", params={"file_id": selected["file_id"]},
            timeout=float(timeout),
        )
        file_response.raise_for_status()
        file_payload = file_response.json()
        file_path = file_payload.get("result", {}).get("file_path")
        if (
            not isinstance(file_path, str)
            or not file_path
            or file_path.startswith("/")
            or any(part in {"", ".", ".."} for part in file_path.split("/"))
            or any(character in file_path for character in ("\\", "?", "#", "\r", "\n"))
        ):
            raise RuntimeError("Telegram file path is invalid")
        download_response = requests.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}",
            timeout=float(timeout),
            stream=True,
        )
        download_response.raise_for_status()
        headers = getattr(download_response, "headers", {}) or {}
        try:
            content_length = headers.get("Content-Length")
        except AttributeError:
            content_length = None
        declared_size = None
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except (TypeError, ValueError):
                declared_size = None
        if declared_size is not None and declared_size > max_bytes:
            raw = None
            close_response = getattr(download_response, "close", None)
            if callable(close_response):
                close_response()
        else:
            chunks = []
            downloaded_size = 0
            for chunk in download_response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                downloaded_size += len(chunk)
                if downloaded_size > max_bytes:
                    chunks = []
                    raw = None
                    close_response = getattr(download_response, "close", None)
                    if callable(close_response):
                        close_response()
                    break
                chunks.append(chunk)
            else:
                raw = b"".join(chunks)

    except (requests.RequestException, ValueError, TypeError, RuntimeError, AttributeError):
        raise RuntimeError("Telegram PDF download failed; check bot access and file availability.") from None

    if raw is None or len(raw) > max_bytes:
        raise RuntimeError(f"Telegram PDF exceeds the 20 MB intake limit (configured limit: {max_bytes} bytes)")
    if not isinstance(raw, (bytes, bytearray)) or not raw.startswith(b"%PDF-"):
        raise RuntimeError("Telegram document is not a valid PDF file")
    return {
        "status": "PDF_READY",
        "update_id": selected["update_id"],
        "next_offset": next_offset,
        "file_name": selected["file_name"],
        "caption": selected["caption"],
        "bytes": bytes(raw),
    }
