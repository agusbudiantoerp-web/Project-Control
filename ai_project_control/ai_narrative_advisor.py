"""Optional Groq/Gemini narrative advisor with evidence-grounded prompts."""
from __future__ import annotations

import json
import requests


def _project_context(metrics: dict, findings=None, action_plan=None) -> dict:
    def records(frame, limit=20):
        if frame is None or getattr(frame, "empty", True):
            return []
        return frame.head(limit).replace({float("nan"): None}).to_dict("records")
    return {
        "calculated_project_metrics": metrics or {},
        "evidence_linked_findings": records(findings),
        "proposed_corrective_actions": records(action_plan),
        "instructions": [
            "Use only the supplied project facts.",
            "Do not invent values, causes, probabilities, dates, owners or contractual interpretations.",
            "Separate measured facts, hypotheses requiring verification, and recommendations.",
            "If evidence is missing, state exactly what is missing.",
            "Prioritize schedule, cost, safety, quality, resource and risk impacts where evidence exists.",
            "Write concise management-ready Indonesian unless the user requests English.",
            "Do not change an approved baseline or imply approval authority.",
        ],
    }


def generate_narrative_advice(
    metrics: dict,
    findings=None,
    action_plan=None,
    provider: str = "Groq",
    groq_api_key: str | None = None,
    gemini_api_key: str | None = None,
    groq_model: str = "llama-3.3-70b-versatile",
    gemini_model: str = "gemini-2.5-flash",
    timeout: int = 45,
) -> dict:
    """Call one configured provider. Never silently switch providers or expose secrets."""
    provider_key = str(provider).strip().lower()
    context = _project_context(metrics, findings, action_plan)
    prompt = (
        "You are a senior project-controls advisor. Produce: (1) executive assessment, "
        "(2) top evidence-backed issues, (3) root-cause hypotheses to verify, "
        "(4) prioritized corrective actions with suggested role owners, "
        "(5) data gaps and next management decisions. Clearly label facts vs hypotheses.\n\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )
    try:
        if provider_key == "groq":
            if not groq_api_key:
                return {"ok": False, "provider": "Groq", "error": "GROQ_API_KEY belum dikonfigurasi pada environment atau Streamlit secrets."}
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": groq_model,
                    "messages": [
                        {"role": "system", "content": "You provide evidence-grounded project controls decision support."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        elif provider_key == "gemini":
            if not gemini_api_key:
                return {"ok": False, "provider": "Gemini", "error": "GEMINI_API_KEY belum dikonfigurasi pada environment atau Streamlit secrets."}
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent",
                params={"key": gemini_api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": "You provide evidence-grounded project controls decision support. Never invent project facts."}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2},
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = "\n".join(
                part.get("text", "") for part in data["candidates"][0]["content"]["parts"]
                if part.get("text")
            )
        else:
            return {"ok": False, "provider": provider, "error": "Provider harus Groq atau Gemini."}
        if not isinstance(answer, str) or not answer.strip():
            return {"ok": False, "provider": provider, "error": "Provider mengembalikan jawaban kosong."}
        return {"ok": True, "provider": provider, "model": groq_model if provider_key == "groq" else gemini_model, "text": answer.strip()}
    except requests.Timeout:
        return {"ok": False, "provider": provider, "error": "Permintaan AI melewati batas waktu. Coba kembali."}
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return {"ok": False, "provider": provider, "error": f"Permintaan provider gagal (HTTP {status or 'network'}). Periksa API key, kuota, model, dan koneksi."}
    except (KeyError, IndexError, TypeError, ValueError):
        return {"ok": False, "provider": provider, "error": "Respons provider tidak sesuai format yang diharapkan."}
