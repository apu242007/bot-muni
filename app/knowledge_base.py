# app/knowledge_base.py
from pathlib import Path

KB_PATH = Path("data/knowledge.txt")

def load_kb() -> str:
    if KB_PATH.exists():
        return KB_PATH.read_text(encoding="utf-8")
    return ""