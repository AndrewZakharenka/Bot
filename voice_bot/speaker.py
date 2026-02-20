"""
speaker.py — преобразование текста в речь.
Шаг 4 пайплайна: текст → звук в динамике

Использует gTTS (Google TTS) — поддерживает русский язык.
Требует интернет. При отсутствии — фолбэк на pyttsx3.
"""
import os
import tempfile

# gTTS + pygame для воспроизведения
try:
    from gtts import gTTS
    import pygame
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False

import pyttsx3

_pyttsx3_engine = None


def _speak_gtts(text: str) -> None:
    """TTS через Google (русский голос, нужен интернет)."""
    tts = gTTS(text=text, lang="ru", slow=False)
    tmp = tempfile.mktemp(suffix=".mp3")
    tts.save(tmp)

    pygame.mixer.init()
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)
    pygame.mixer.music.unload()
    pygame.mixer.quit()
    os.remove(tmp)


def _speak_pyttsx3(text: str) -> None:
    """Фолбэк: TTS через pyttsx3 (системные голоса, офлайн)."""
    global _pyttsx3_engine
    if _pyttsx3_engine is None:
        _pyttsx3_engine = pyttsx3.init()
        _pyttsx3_engine.setProperty("rate", 160)
        _pyttsx3_engine.setProperty("volume", 1.0)
    _pyttsx3_engine.say(text)
    _pyttsx3_engine.runAndWait()


def speak(text: str) -> None:
    """Произносит текст вслух. Использует gTTS если доступен, иначе pyttsx3."""
    print(f"[Speaker] Говорю: '{text}'")
    if _GTTS_AVAILABLE:
        try:
            _speak_gtts(text)
            return
        except Exception as e:
            print(f"[Speaker] gTTS не сработал ({e}), пробую pyttsx3...")
    _speak_pyttsx3(text)
