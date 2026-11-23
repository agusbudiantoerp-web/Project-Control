import pytest

from ai_project_control.telegram_executive_reporting import (
    build_telegram_executive_message,
    send_telegram_executive_message,
    split_telegram_message,
)


def test_message_uses_only_supplied_summary_values():
    message = build_telegram_executive_message(
        project_name="Plant Upgrade",
        status_date="2026-11-23",
        intelligence={"summary": {
            "project_count": 2, "p1_count": 1, "p2_count": 0,
            "critical_risk_count": 1, "high_risk_count": 0,
            "insufficient_performance_data_count": 1,
        }},
        action_register={"summary": {"open_count": 2, "in_progress_count": 1,
                                     "blocked_count": 0, "overdue_count": 1}},
    )
    assert "Plant Upgrade" in message
    assert "P1 immediate review: 1" in message
    assert "Overdue: 1" in message
    assert "Screening information only" in message


def test_message_chunking_preserves_content_and_limit():
    source = ("Line of report.\n" * 800)
    chunks = split_telegram_message(source, limit=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "".join(chunks) == source


def test_chunk_limit_must_be_reasonable():
    with pytest.raises(ValueError):
        split_telegram_message("hello", limit=20)


def test_missing_credentials_are_rejected_before_network():
    with pytest.raises(ValueError, match="token"):
        send_telegram_executive_message(bot_token="", chat_id="123", message="hello")
    with pytest.raises(ValueError, match="chat ID"):
        send_telegram_executive_message(bot_token="123:abc", chat_id="", message="hello")
