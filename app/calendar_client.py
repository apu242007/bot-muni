# app/calendar_client.py
from datetime import datetime, timedelta
from dateutil import tz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.settings import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def is_busy(start_dt: datetime, end_dt: datetime) -> bool:
    service = get_service()
    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "timeZone": settings.TIMEZONE,
        "items": [{"id": settings.GOOGLE_CALENDAR_ID}],
    }
    fb = service.freebusy().query(body=body).execute()
    busy = fb["calendars"][settings.GOOGLE_CALENDAR_ID].get("busy", [])
    return len(busy) > 0

def create_event(summary: str, description: str, start_dt: datetime, end_dt: datetime, attendee_phone: str):
    service = get_service()
    event = {
        "summary": summary,
        "description": f"{description}\nTel: {attendee_phone}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": settings.TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": settings.TIMEZONE},
    }
    created = service.events().insert(calendarId=settings.GOOGLE_CALENDAR_ID, body=event).execute()
    return created.get("id"), created.get("htmlLink")