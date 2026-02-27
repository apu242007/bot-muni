#transcribir audio

# app/audio.py
from pathlib import Path

def transcribe_audio_local(audio_path: str) -> str:
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, language="es")
        text = " ".join([seg.text.strip() for seg in segments]).strip()
        return text
    except Exception as e:
        return ""