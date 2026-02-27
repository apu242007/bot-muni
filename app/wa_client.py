import requests
from app.settings import settings

GRAPH = "https://graph.facebook.com/v20.0"

def send_text(to_phone: str, text:str):
    url=f"{GRAPH}/{settings.WA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text[:3800]}  # limite de wpp
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    return r.status_code, r.text

def get_media_url(media_id: str) -> str:
    url = f"{GRAPH}/{media_id}"
    headers = {
        "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["url"]

def download_media(media_url: str, out_path: str):
    headers = {"Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}"}
    with requests.get(media_url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)