import json
from unittest.mock import patch

import pytest

from ai_project_control.telegram_notifications import (
    format_escalation_message,
    send_telegram_message,
)


def test_format_escalation_message_contains_summary_and_action():
    result = {
        "as_of": "2026-11-23",
        "summary": {"escalation_count": 1, "director_count": 1, "manager_count": 0},
        "escalations": [{
            "action_id": "ACT-1", "title": "Recover critical path",
            "project_id": "PRJ-1", "priority": "P1", "status": "BLOCKED",
            "due_date": "2026-11-20", "owner": "PM",
            "escalation_level": "PROJECT_DIRECTOR", "reason": "P1_ACTION_BLOCKED",
            "recommended_action": "Assign unblock owner",
        }],
    }
    message = format_escalation_message(result)
    assert "Total eskalasi: 1" in message
    assert "Recover critical path" in message
    assert "Assign unblock owner" in message


def test_format_limits_message_length():
    result = {"as_of": "2026-11-23", "summary": {}, "escalations": [
        {"action_id": str(i), "title": "X" * 300, "recommended_action": "Y" * 300}
        for i in range(40)
    ]}
    assert len(format_escalation_message(result)) <= 3900


def test_missing_credentials_rejected():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            send_telegram_message("hello")


def test_empty_message_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        send_telegram_message(" ", bot_token="token", chat_id="chat")


def test_successful_delivery_uses_telegram_api():
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"ok": True, "result": {"message_id": 123}}).encode()

    with patch("ai_project_control.telegram_notifications.urlopen", return_value=FakeResponse()) as mocked:
        result = send_telegram_message("hello", bot_token="secret", chat_id="123")
    assert result == {"status": "SENT", "message_id": 123}
    request = mocked.call_args.args[0]
    assert "secret" in request.full_url
    assert "secret" not in repr(result)


def test_telegram_api_rejection_is_reported_without_credentials():
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"ok": False, "description": "chat not found"}).encode()

    with patch("ai_project_control.telegram_notifications.urlopen", return_value=FakeResponse()):
        with pytest.raises(RuntimeError, match="chat not found"):
            send_telegram_message("hello", bot_token="secret", chat_id="123")
