#flujo de turnos
# app/flows.py
import re
from datetime import datetime, timedelta
from dateutil import tz, parser
from app.settings import settings
from app import calendar_client

# ---------- MENÚ ----------
def is_greeting(text: str) -> bool:
    t = text.lower().strip()
    return t in {"hola", "menu", "menú", "buenas", "buen día", "buen dia", "buenas tardes", "buenas noches", "inicio"}

def menu_text() -> str:
    return (
        "👋 Hola! Soy el bot de la Subsecretaría de Capacitación.\n"
        "Elegí una opción:\n"
        "1) Sacar turno presencial\n"
        "2) Requisitos Becas (Inicial/Primario/Secundario)\n"
        "3) Requisitos Becas (Terciario/Universitario)\n"
        "4) Carreras 2026 (Descuentos)\n"
        "5) Convenios especiales\n"
        "6) Hablar con una persona\n\n"
        "Respondé con el número."
    )

def menu_choice(text: str) -> str | None:
    t = text.strip()
    return t if t in {"1","2","3","4","5","6"} else None

# ---------- TURNOS ----------
def looks_like_booking(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["turno", "agenda", "agendar", "cita", "reservar", "sacar turno"])

def looks_like_cancel(text: str) -> bool:
    t = text.lower()
    return "cancel" in t and "turn" in t  # "cancelar turno", "cancela el turno"

def parse_datetime_es(text: str):
    """
    MVP: 'mañana 10', '01/03 10:30', '2026-03-01 11:00'
    """
    t = text.lower().strip()
    now = datetime.now(tz=tz.gettz(settings.TIMEZONE))

    if "mañana" in t:
        m = re.search(r"(\d{1,2})(?::(\d{2}))?", t)
        if not m:
            return None
        hh = int(m.group(1))
        mm = int(m.group(2) or "0")
        return (now + timedelta(days=1)).replace(hour=hh, minute=mm, second=0, microsecond=0)

    try:
        dt = parser.parse(text, dayfirst=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.gettz(settings.TIMEZONE))
        return dt
    except:
        return None

def within_office_hours(dt: datetime) -> bool:
    if dt.weekday() >= 5:  # sábado=5, domingo=6
        return False
    h = dt.hour + dt.minute/60
    return (h >= 8.0) and (h < 21.0)

def format_dt(dt: datetime) -> str:
    return dt.strftime("%d/%m %H:%M")

def offer_alternatives(dt: datetime, duration: timedelta):
    return [dt + duration, dt + duration*2]

def try_book_slot(phone: str, user_text: str):
    dt = parse_datetime_es(user_text)
    if not dt:
        return (False,
                "Dale 😊 Decime *qué día y hora* querés el turno.\n"
                "Ejemplos: `mañana 10:30`, `01/03 09:00`, `2026-03-01 11:00`.")

    if not within_office_hours(dt):
        return (False,
                "⏰ Los turnos se dan de *lunes a viernes de 08:00 a 21:00*.\n"
                "Decime un día y hora dentro de ese horario (ej: `mañana 10:00`).")

    duration = timedelta(minutes=settings.DEFAULT_SLOT_MINUTES)
    end_dt = dt + duration

    if calendar_client.is_busy(dt, end_dt):
        alts = offer_alternatives(dt, duration)
        # devolvemos alternativas para que el main las guarde en contexto
        reply = (
            f"Ese horario ya está ocupado.\n"
            f"¿Te sirve alguno de estos?\n"
            f"1) {format_dt(alts[0])}\n"
            f"2) {format_dt(alts[1])}\n\n"
            "Respondé con *1* o *2*, o enviame otra fecha/hora."
        )
        return (False, reply, alts)

    event_id, link = calendar_client.create_event(
        summary="Turno - Subsecretaría de Capacitación",
        description="Atención presencial para información / trámites.",
        start_dt=dt,
        end_dt=end_dt,
        attendee_phone=phone
    )
    return (True,
            f"✅ Turno confirmado:\n"
            f"📅 {dt.strftime('%d/%m/%Y')} a las {dt.strftime('%H:%M')} (duración {settings.DEFAULT_SLOT_MINUTES} min)\n"
            f"Si necesitás cancelar, decime: *cancelar turno*.")

def book_from_alternatives(phone: str, alt_dt: datetime):
    duration = timedelta(minutes=settings.DEFAULT_SLOT_MINUTES)
    if not within_office_hours(alt_dt):
        return (False, "Ese horario alternativo no está dentro del horario de atención. Enviame otro día/hora.")
    if calendar_client.is_busy(alt_dt, alt_dt + duration):
        return (False, "Ese horario alternativo se ocupó recién. Enviame otro día/hora.")
    calendar_client.create_event(
        summary="Turno - Subsecretaría de Capacitación",
        description="Atención presencial para información / trámites.",
        start_dt=alt_dt,
        end_dt=alt_dt + duration,
        attendee_phone=phone
    )
    return (True,
            f"✅ Turno confirmado:\n"
            f"📅 {alt_dt.strftime('%d/%m/%Y')} a las {alt_dt.strftime('%H:%M')} (duración {settings.DEFAULT_SLOT_MINUTES} min)\n"
            f"Si necesitás cancelar, decime: *cancelar turno*.")