# app/main.py
import os
import hmac
import hashlib

from fastapi import FastAPI, Request, Response, Depends, Header, HTTPException
from pydantic import BaseModel
from dateutil import parser as dtparser

from app.settings import settings
from app.db import (
    init_db, upsert_user, log_message,
    get_state, set_state, get_context, set_context
)
from app.wa_client import send_text, get_media_url, download_media
from app.audio import transcribe_audio_local
from app.agent import chat
from app.flows import (
    is_greeting, menu_text, menu_choice,
    looks_like_booking, try_book_slot,
    book_from_alternatives
)

# --------- APP ---------
app = FastAPI()

# --------- DEPENDENCIAS ---------
def verify_test_key(x_test_api_key: str = Header(default="")):
    """Dependencia que protege los endpoints /test/ con un header X-Test-API-Key."""
    if not settings.TEST_API_KEY:
        raise HTTPException(status_code=403, detail="TEST_API_KEY no configurada en el servidor.")
    if not hmac.compare_digest(settings.TEST_API_KEY, x_test_api_key):
        raise HTTPException(status_code=403, detail="X-Test-API-Key inválida.")

# --------- MODELOS ---------
class TestMsg(BaseModel):
    phone: str
    text: str

class TestReset(BaseModel):
    phone: str

# --------- HELPERS ---------
def handle_incoming(phone: str, text_in: str) -> str:
    """Usado por los endpoints /test/ para simular mensajes entrantes."""
    upsert_user(phone)
    log_message(phone, "in", text_in)

    if looks_like_booking(text_in):
        result = try_book_slot(phone, text_in)
        if isinstance(result, tuple) and len(result) >= 2:
            reply = result[1]
        else:
            reply = "Error procesando turno."
        log_message(phone, "out", reply)
        return reply

    reply = chat(text_in, history=[])
    log_message(phone, "out", reply)
    return reply


def _handle_booking_result(phone: str, result):
    """
    try_book_slot puede devolver:
      - (ok, reply)
      - (ok, reply, alts[list[datetime]])
    """
    if isinstance(result, tuple) and len(result) == 2:
        ok, reply = result
        if ok:
            set_state(phone, "idle")
            set_context(phone, {})
        else:
            set_state(phone, "booking")
        return reply

    if isinstance(result, tuple) and len(result) == 3:
        ok, reply, alts = result
        if (not ok) and alts:
            set_state(phone, "waiting_alt")
            set_context(phone, {"alts": [a.isoformat() for a in alts]})
        else:
            set_state(phone, "idle")
            set_context(phone, {})
        return reply

    # fallback
    set_state(phone, "idle")
    set_context(phone, {})
    return "Tuve un problema procesando el turno. Probá de nuevo con `mañana 10:00`."


# --------- STARTUP ---------
@app.on_event("startup")
def _startup():
    init_db()

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WA_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Invalid token", status_code=403)

@app.post("/webhook")
async def webhook(request: Request):
    # -------- validación HMAC-SHA256 (Meta X-Hub-Signature-256) --------
    if settings.WA_APP_SECRET:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        body_bytes = await request.body()
        expected = hmac.new(
            settings.WA_APP_SECRET.encode(),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(f"sha256={expected}", sig_header):
            return Response(content="Invalid signature", status_code=403)
        import json as _json
        data = _json.loads(body_bytes)
    else:
        data = await request.json()

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        msg = value["messages"][0]
        phone = msg["from"]
        upsert_user(phone)

        # -------- leer entrada (texto o audio) --------
        text_in = None

        if msg.get("type") == "text":
            text_in = msg["text"]["body"].strip()

        elif msg.get("type") == "audio":
            audio_id = msg["audio"]["id"]
            media_url = get_media_url(audio_id)
            os.makedirs("tmp", exist_ok=True)
            path = f"tmp/{audio_id}.ogg"
            download_media(media_url, path)

            text_in = transcribe_audio_local(path).strip()
            if not text_in:
                reply = "Recibí tu audio, pero no pude transcribirlo todavía. ¿Podés escribirlo en texto?"
                send_text(phone, reply)
                log_message(phone, "out", reply)
                return {"status": "ok"}

        else:
            reply = "Por ahora puedo procesar texto o audio 😊"
            send_text(phone, reply)
            log_message(phone, "out", reply)
            return {"status": "ok"}

        log_message(phone, "in", text_in)

        # -------- router principal --------
        state = get_state(phone)
        ctx = get_context(phone)

        # 0) Saludo → menú
        if is_greeting(text_in):
            reply = menu_text()
            send_text(phone, reply)
            log_message(phone, "out", reply)
            return {"status": "ok"}

        # 1) Si está esperando alternativa 1/2
        if state == "waiting_alt":
            choice = text_in.strip()
            if choice in {"1", "2"} and isinstance(ctx.get("alts"), list) and len(ctx["alts"]) >= 2:
                idx = 0 if choice == "1" else 1
                alt_dt = dtparser.parse(ctx["alts"][idx])

                ok, reply = book_from_alternatives(phone, alt_dt)
                send_text(phone, reply)
                log_message(phone, "out", reply)

                set_state(phone, "idle")
                set_context(phone, {})
                return {"status": "ok"}

            # si no mandó 1/2, lo dejamos elegir otra fecha/hora
            # si manda una fecha/hora, lo tratamos como nuevo intento:
            if looks_like_booking(text_in) or state == "waiting_alt":
                result = try_book_slot(phone, text_in)
                reply = _handle_booking_result(phone, result)
                send_text(phone, reply)
                log_message(phone, "out", reply)
                return {"status": "ok"}

        # 2) Menú numérico
        choice = menu_choice(text_in)
        if choice:
            if choice == "1":
                set_state(phone, "booking")
                reply = "Perfecto 😊 Decime *día y hora* para tu turno (lun-vie 08:00-21:00). Ej: `mañana 10:00`"
                send_text(phone, reply)
                log_message(phone, "out", reply)
                return {"status": "ok"}

            if choice == "6":
                # acá podrías disparar una notificación interna o guardar en DB para atención humana
                reply = "📌 Listo. Dejanos tu consulta y tu nombre, y te contacta una persona apenas pueda."
                send_text(phone, reply)
                log_message(phone, "out", reply)
                return {"status": "ok"}

            # 2 a 5: respuesta IA usando knowledge
            reply = chat(f"El usuario eligió la opción {choice}. Respondé con la info correspondiente.", history=[])
            send_text(phone, reply)
            log_message(phone, "out", reply)
            return {"status": "ok"}

        # 3) Booking: si está en modo booking o detecta intención de turno
        if state == "booking" or looks_like_booking(text_in):
            result = try_book_slot(phone, text_in)
            reply = _handle_booking_result(phone, result)
            send_text(phone, reply)
            log_message(phone, "out", reply)
            return {"status": "ok"}

        # 4) Default: IA general con knowledge
        reply = chat(text_in, history=[])
        send_text(phone, reply)
        log_message(phone, "out", reply)
        return {"status": "ok"}

    except Exception as e:
        return {"status": "error", "detail": str(e)}


# --------- ENDPOINTS DE TEST ---------
@app.post("/test/message", dependencies=[Depends(verify_test_key)])
async def test_message(payload: TestMsg):
    """
    Postman: POST http://localhost:8000/test/message
    Header:  X-Test-API-Key: <valor de TEST_API_KEY en .env>
    Body JSON: {"phone":"+549XXXXXXXXXX","text":"hola"}
    """
    reply = handle_incoming(payload.phone, payload.text.strip())
    return {"reply": reply}

@app.get("/test/state", dependencies=[Depends(verify_test_key)])
async def test_state(phone: str):
    """
    GET http://localhost:8000/test/state?phone=+549...
    Header: X-Test-API-Key: <valor de TEST_API_KEY en .env>
    """
    return {
        "phone": phone,
        "state": get_state(phone),
        "context": get_context(phone)
    }

@app.post("/test/reset", dependencies=[Depends(verify_test_key)])
async def test_reset(payload: TestReset):
    """
    POST http://localhost:8000/test/reset
    Header:  X-Test-API-Key: <valor de TEST_API_KEY en .env>
    Body JSON: {"phone":"+549..."}
    """
    set_state(payload.phone, "idle")
    set_context(payload.phone, {})
    return {"status": "ok", "phone": payload.phone}
