"""
transcriber.py — преобразование речи в текст через Whisper.
Шаг 2 пайплайна: WAV-файл → текст

Модели Whisper (от быстрее/хуже к медленнее/лучше):
  "tiny"   ~39 MB  — очень быстро, хуже качество
  "base"   ~74 MB  — хороший баланс (по умолчанию)
  "small"  ~244 MB — лучше качество
  "medium" ~769 MB — высокое качество, медленно на CPU
"""
import os
import shutil
import imageio_ffmpeg
import whisper

# imageio_ffmpeg хранит бинарник как ffmpeg-win-x86_64-vX.Y.exe
# Whisper ищет просто "ffmpeg" — создаём копию с нужным именем
_ffmpeg_src = imageio_ffmpeg.get_ffmpeg_exe()
_ffmpeg_dir = os.path.dirname(_ffmpeg_src)
_ffmpeg_dst = os.path.join(_ffmpeg_dir, "ffmpeg.exe")
if not os.path.exists(_ffmpeg_dst):
    shutil.copy(_ffmpeg_src, _ffmpeg_dst)

# Добавляем директорию в начало PATH (prepend важен — иначе может найти другой)
os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# Модель загружается один раз при первом вызове
_model = None


def _get_model(name: str = "small"):
    global _model
    if _model is None:
        print(f"[Transcriber] Загружаю модель Whisper '{name}' (первый запуск — нужно подождать)...")
        _model = whisper.load_model(name)
        print("[Transcriber] Модель загружена.")
    return _model


def transcribe(audio_path: str, language: str = "ru") -> str:
    """
    Принимает путь к WAV-файлу, возвращает распознанный текст.

    audio_path — путь к WAV-файлу
    language   — язык для подсказки Whisper ("ru", "en", и т.д.)
                 Можно убрать — Whisper определит сам, но медленнее.
    """
    model = _get_model()

    print("[Transcriber] Распознаю речь...")
    result = model.transcribe(audio_path, language=language)
    text = result["text"].strip()

    print(f"[Transcriber] Распознано: '{text}'")
    return text
