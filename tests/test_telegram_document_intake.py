import pytest

import ai_project_control.telegram_document_intake as intake


class Response:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetches_latest_authorized_pdf_and_returns_next_offset(monkeypatch):
    calls = []
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 100,
            "message": {
                "chat": {"id": -100123},
                "document": {
                    "file_id": "FILE-1", "file_name": "drawing.pdf",
                    "mime_type": "application/pdf", "file_size": 9,
                },
                "caption": "Latest drawing",
            },
        }]}),
        Response({"ok": True, "result": {"file_path": "documents/drawing.pdf"}}),
        Response(content=b"%PDF-1.7 test"),
    ]

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(intake.requests, "get", fake_get)
    result = intake.fetch_latest_telegram_pdf(
        "bot-token", "-100123", offset=90
    )
    assert result["status"] == "PDF_READY"
    assert result["file_name"] == "drawing.pdf"
    assert result["caption"] == "Latest drawing"
    assert result["bytes"].startswith(b"%PDF-")
    assert result["next_offset"] == 101
    assert calls[0][1]["params"]["offset"] == 90
    assert calls[1][1]["params"]["file_id"] == "FILE-1"


def test_ignores_documents_from_unauthorized_chats(monkeypatch):
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: Response({
        "ok": True,
        "result": [{
            "update_id": 7,
            "message": {
                "chat": {"id": "999"},
                "document": {"file_id": "F", "file_name": "x.pdf"},
            },
        }],
    }))
    result = intake.fetch_latest_telegram_pdf("token", "123")
    assert result == {"status": "NO_PDF", "next_offset": 8}


def test_rejects_non_pdf_download(monkeypatch):
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 1,
            "message": {
                "chat": {"id": "123"},
                "document": {"file_id": "F", "file_name": "drawing.pdf"},
            },
        }]}),
        Response({"ok": True, "result": {"file_path": "documents/drawing.pdf"}}),
        Response(content=b"not a pdf"),
    ]
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(RuntimeError, match="not a valid PDF"):
        intake.fetch_latest_telegram_pdf("token", "123")


def test_rejects_invalid_credentials_and_offsets_before_network():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        intake.fetch_latest_telegram_pdf("", "123")
    with pytest.raises(ValueError, match="TELEGRAM_CHAT_ID"):
        intake.fetch_latest_telegram_pdf("token", "")
    with pytest.raises(ValueError, match="offset"):
        intake.fetch_latest_telegram_pdf("token", "123", offset=True)


def test_rejects_custom_limit_above_telegram_cap_before_network():
    with pytest.raises(ValueError, match="20 MB"):
        intake.fetch_latest_telegram_pdf(
            "token", "123", max_bytes=intake.MAX_TELEGRAM_PDF_BYTES + 1
        )


@pytest.mark.parametrize("unsafe_path", ["../outside.pdf", "documents/file.pdf?x=1", "documents\\\\file.pdf"])
def test_rejects_unsafe_telegram_file_paths(monkeypatch, unsafe_path):
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 1,
            "message": {
                "chat": {"id": "123"},
                "document": {"file_id": "F", "file_name": "drawing.pdf"},
            },
        }]}),
        Response({"ok": True, "result": {"file_path": unsafe_path}}),
    ]
    calls = []
    def fake_get(url, **kwargs):
        calls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(intake.requests, "get", fake_get)
    with pytest.raises(RuntimeError, match="Telegram PDF download failed"):
        intake.fetch_latest_telegram_pdf("token", "123")
    assert len(calls) == 2
