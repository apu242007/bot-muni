# app/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "")
    WA_APP_SECRET = os.getenv("WA_APP_SECRET", "")  # App Secret de Meta (para validar firma HMAC)
    WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID", "")
    WA_ACCESS_TOKEN = os.getenv("WA_ACCESS_TOKEN", "")
    BASE_URL = os.getenv("BASE_URL", "")

    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")

    BOT_NAME = os.getenv("BOT_NAME", "Bot Turnos")
    DEFAULT_SLOT_MINUTES = int(os.getenv("DEFAULT_SLOT_MINUTES", "30"))

    TEST_API_KEY = os.getenv("TEST_API_KEY", "")  # Protege los endpoints /test/

    AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

settings = Settings()