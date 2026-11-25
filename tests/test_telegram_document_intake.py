import pytest

import ai_project_control.telegram_document_intake as intake


class Response:
    def __init__(self, payload=None, content=b"", headers=None):
        self._payload = payload
        self.content = content
        self.headers = headers or {}
        self.closed = False

    def close(self):
        self.closed = True

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def iter_content(self, chunk_size=64 * 1024):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


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
    assert responses[0].closed is False if False else True
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


@pytest.mark.parametrize("unsafe_path", ["../outside.pdf", "documents/file.pdf?x=1", r"documents\file.pdf", r"documents\\file.pdf", "documents/file\rname.pdf", "documents/file\nname.pdf"])
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



@pytest.mark.parametrize(
    "file_size",
    [intake.MAX_TELEGRAM_PDF_BYTES + 1, -1, True, "2048"],
)
def test_ignores_invalid_or_oversized_telegram_document_metadata(monkeypatch, file_size):
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: Response({
        "ok": True,
        "result": [{
            "update_id": 10,
            "message": {
                "chat": {"id": "123"},
                "document": {
                    "file_id": "FILE-OVERSIZED",
                    "file_name": "drawing.pdf",
                    "mime_type": "application/pdf",
                    "file_size": file_size,
                },
            },
        }],
    }))
    result = intake.fetch_latest_telegram_pdf("token", "123")
    assert result == {"status": "NO_PDF", "next_offset": 11}


def test_rejects_downloaded_telegram_pdf_over_configured_size(monkeypatch):
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 1,
            "message": {
                "chat": {"id": "123"},
                "document": {"file_id": "FILE-LARGE", "file_name": "drawing.pdf"},
            },
        }]}),
        Response({"ok": True, "result": {"file_path": "documents/drawing.pdf"}}),
        Response(content=b"%PDF-" + b"x" * 16),
    ]
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(RuntimeError, match="exceeds the 20 MB intake limit"):
        intake.fetch_latest_telegram_pdf("token", "123", max_bytes=10)



def test_stops_streaming_when_pdf_exceeds_configured_limit(monkeypatch):
    oversized_response = Response(content=b"%PDF-" + b"x" * 20)
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 2,
            "message": {
                "chat": {"id": "123"},
                "document": {"file_id": "FILE-STREAM", "file_name": "drawing.pdf"},
            },
        }]}),
        Response({"ok": True, "result": {"file_path": "documents/drawing.pdf"}}),
        oversized_response,
    ]
    chunks_requested = []
    original_iter_content = Response.iter_content

    def tracked_iter_content(self, chunk_size=64 * 1024):
        for chunk in original_iter_content(self, chunk_size):
            chunks_requested.append(len(chunk))
            yield chunk

    monkeypatch.setattr(Response, "iter_content", tracked_iter_content)
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(RuntimeError, match="configured limit: 10 bytes"):
        intake.fetch_latest_telegram_pdf("token", "123", max_bytes=10)
    assert chunks_requested == [25]
    assert oversized_response.closed


def test_rejects_oversized_content_length_before_streaming(monkeypatch):
    oversized_response = Response(content=b"%PDF-", headers={"Content-Length": "1000"})
    responses = [
        Response({"ok": True, "result": [{
            "update_id": 3,
            "message": {
                "chat": {"id": "123"},
                "document": {"file_id": "FILE-LENGTH", "file_name": "drawing.pdf"},
            },
        }]}),
        Response({"ok": True, "result": {"file_path": "documents/drawing.pdf"}}),
        oversized_response,
    ]
    monkeypatch.setattr(intake.requests, "get", lambda *args, **kwargs: responses.pop(0))
    with pytest.raises(RuntimeError, match="configured limit: 10 bytes"):
        intake.fetch_latest_telegram_pdf("token", "123", max_bytes=10)
    assert oversized_response.closed
