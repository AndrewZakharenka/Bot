"""
recorder.py — запись звука с микрофона.
Шаг 1 пайплайна: Микрофон → WAV-файл
"""
import tempfile
import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

SAMPLE_RATE = 16000  # Whisper ожидает 16 kHz
CHANNELS = 1         # моно


def record(seconds: int = 5) -> str:
    """
    Записывает звук с микрофона.
    Возвращает путь к временному WAV-файлу.

    seconds — длительность записи в секундах.
    """
    print(f"[Recorder] Говори... ({seconds} сек)")

    audio = sd.rec(
        frames=int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()  # ждём пока запись закончится

    print("[Recorder] Запись завершена.")

    # Сохраняем во временный файл — Whisper читает с диска
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.write(tmp.name, SAMPLE_RATE, audio)
    return tmp.name


def delete(path: str) -> None:
    """Удаляет временный аудиофайл после обработки."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
