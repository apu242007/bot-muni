# app/agent.py
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

def ollama_chat(user_text: str, history: list[dict]) -> str:
    kb = load_kb()
    prompt = f"{SYSTEM_PROMPT}\n\nBASE DE CONOCIMIENTO:\n{kb}\n\nUSUARIO: {user_text}\n"

    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": (
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "system", "content": f"BASE DE CONOCIMIENTO:\n{kb}"}]
            + history
            + [{"role": "user", "content": user_text}]
        ),
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()

def openai_chat(user_text: str, history: list[dict]) -> str:
    # Implementación mínima con requests (sin SDK)
    import json
    kb = load_kb()
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": (
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "system", "content": f"BASE DE CONOCIMIENTO:\n{kb}"}]
            + history
            + [{"role": "user", "content": user_text}]
        )
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def chat(user_text: str, history: list[dict]) -> str:
    if settings.AI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            return "Falta configurar OPENAI_API_KEY."
        return openai_chat(user_text, history)
    return ollama_chat(user_text, history)