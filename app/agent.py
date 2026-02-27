# app/agent.py
import json
import requests
from app.settings import settings
from app.knowledge_base import load_kb

SYSTEM_PROMPT = """
Sos un asistente oficial de la Subsecretaría de Capacitación.
Tu tarea:
- responder consultas de trámites y requisitos usando la base de conocimiento.
- guiar para sacar turnos.
- NO inventar requisitos. Si falta info, pedir datos mínimos o indicar que debe confirmarse en la oficina.
- ser claro, breve y amable.

Cuando el usuario pida turno:
- confirmá día y hora.
- confirmá nombre y trámite.
- recordá duración estándar del turno.
"""

def _system_with_kb() -> str:
    """Devuelve el system prompt completo con la KB embebida."""
    kb = load_kb()
    return f"{SYSTEM_PROMPT}\n\nBASE DE CONOCIMIENTO:\n{kb}"


def ollama_chat(user_text: str, history: list[dict]) -> str:
    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": (
            [{"role": "system", "content": _system_with_kb()}]
            + history
            + [{"role": "user", "content": user_text}]
        ),
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()

def openai_chat(user_text: str, history: list[dict]) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": (
            [{"role": "system", "content": _system_with_kb()}]
            + history
            + [{"role": "user", "content": user_text}]
        ),
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def gemini_chat(user_text: str, history: list[dict]) -> str:
    """
    Llama a la API REST de Gemini (sin SDK).
    Modelo por defecto: gemini-2.0-flash (gratuito en el tier free).
    Docs: https://ai.google.dev/api/generate-content
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )

    # Historial: OpenAI usa "assistant", Gemini usa "model"
    def to_gemini_role(role: str) -> str:
        return "model" if role == "assistant" else role

    contents = [
        {"role": to_gemini_role(m["role"]), "parts": [{"text": m["content"]}]}
        for m in history
        if m["role"] in {"user", "assistant"}
    ]
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "system_instruction": {"parts": [{"text": _system_with_kb()}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
        },
    }

    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return "No pude generar una respuesta. Intentá de nuevo."

def chat(user_text: str, history: list[dict]) -> str:
    provider = settings.AI_PROVIDER

    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            return "Falta configurar GEMINI_API_KEY en el .env."
        return gemini_chat(user_text, history)

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            return "Falta configurar OPENAI_API_KEY en el .env."
        return openai_chat(user_text, history)

    # Fallback: Ollama local
    return ollama_chat(user_text, history)