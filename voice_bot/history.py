"""
history.py — хранение истории встреч в JSON-файлах.

Файлы сохраняются в Bot/meetings/YYYY-MM-DD_HH-MM-SS.json
Поля: date, duration_sec, transcript, mom
"""
import json
import os
from datetime import datetime

MEETINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "meetings")


def _ensure_dir():
    os.makedirs(MEETINGS_DIR, exist_ok=True)


def save(transcript: str, mom: str, duration_sec: float) -> str:
    """
    Сохраняет встречу в JSON-файл.
    Возвращает путь к файлу.
    """
    _ensure_dir()
    now = datetime.now()
    filename = now.strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    path = os.path.join(MEETINGS_DIR, filename)

    data = {
        "date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": round(duration_sec),
        "transcript": transcript,
        "mom": mom,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[History] Встреча сохранена: {filename}")
    return path


def load_all() -> list[dict]:
    """
    Загружает все встречи из meetings/.
    Возвращает список dict, отсортированный от новых к старым.
    """
    _ensure_dir()
    meetings = []

    for fname in sorted(os.listdir(MEETINGS_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(MEETINGS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filename"] = fname
                meetings.append(data)
        except Exception as e:
            print(f"[History] Не удалось прочитать {fname}: {e}")

    return meetings
