from types import SimpleNamespace

import requests

from ai_project_control import ai_narrative_advisor as advisor


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_groq_advisor_uses_authorization_header_and_validated_timeout(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({"choices": [{"message": {"content": "Review the critical path."}}]})

    monkeypatch.setattr(advisor.requests, "post", fake_post)
    result = advisor.generate_narrative_advice(
        {"SPI": 0.9}, provider="Groq", groq_api_key=" secret-token ",
        timeout=12,
    )
    assert result["ok"] is True
    assert result["text"] == "Review the critical path."
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["timeout"] == 12.0


def test_gemini_advisor_sends_api_key_in_header_not_url(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({
            "candidates": [{
                "content": {"parts": [{"text": "Periksa progres dan biaya."}]}
            }]
        })

    monkeypatch.setattr(advisor.requests, "post", fake_post)
    result = advisor.generate_narrative_advice(
        {"CPI": 0.95}, provider="Gemini", gemini_api_key=" gemini-secret ",
        timeout=8,
    )
    assert result["ok"] is True
    assert result["text"] == "Periksa progres dan biaya."
    assert captured["headers"]["x-goog-api-key"] == "gemini-secret"
    assert "gemini-secret" not in captured["url"]
    assert "params" not in captured
    assert captured["timeout"] == 8.0


def test_advisor_rejects_invalid_model_and_nonpositive_timeout(monkeypatch):
    called = False

    def fake_post(*args, **kwargs):
        nonlocal called
        called = True
        return FakeResponse({})

    monkeypatch.setattr(advisor.requests, "post", fake_post)
    invalid_model = advisor.generate_narrative_advice(
        {}, provider="Gemini", gemini_api_key="key", gemini_model="../unsafe",
    )
    invalid_timeout = advisor.generate_narrative_advice(
        {}, provider="Groq", groq_api_key="key", timeout=float("inf"),
    )
    assert invalid_model["ok"] is False
    assert invalid_timeout["ok"] is False
    assert called is False


def test_advisor_does_not_echo_secret_on_network_failure(monkeypatch):
    secret = "sensitive-token"

    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("failed URL contained " + secret)

    monkeypatch.setattr(advisor.requests, "post", fake_post)
    result = advisor.generate_narrative_advice(
        {}, provider="Groq", groq_api_key=secret,
    )
    assert result["ok"] is False
    assert secret not in result["error"]
