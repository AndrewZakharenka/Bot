"""
transcriber.py — преобразование речи в текст через Whisper.
Шаг 2 пайплайна: WAV-файл → текст

Модели Whisper (от быстрее/хуже к медленнее/лучше):
  "tiny"   ~39 MB  — очень быстро, хуже качество
  "base"   ~74 MB  — базовый
  "small"  ~244 MB — хороший баланс
  "medium" ~769 MB — высокое качество (по умолчанию для встреч)
  "large"  ~1.5 GB — максимальное качество, очень медленно на CPU
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
_model_name = None

# Параметры для качественного распознавания
_TRANSCRIBE_OPTS = dict(
    temperature=0,                    # детерминированный вывод
    beam_size=5,                      # лучший beam search
    condition_on_previous_text=False, # False = точнее timestamps (не "тянет" текст вперёд)
    no_speech_threshold=0.6,          # фильтрует тишину и шум
    compression_ratio_threshold=2.4,
    initial_prompt="Это деловая встреча или разговор на русском языке.",
)


def _get_model(name: str = "medium"):
    global _model, _model_name
    if _model is None or _model_name != name:
        print(f"[Transcriber] Загружаю модель Whisper '{name}' (первый запуск — нужно подождать)...")
        _model = whisper.load_model(name)
        _model_name = name
        print("[Transcriber] Модель загружена.")
    return _model


def transcribe(audio_path: str, language: str = "ru") -> str:
    """
    Принимает путь к WAV-файлу, возвращает распознанный текст.

    audio_path — путь к WAV-файлу
    language   — язык для подсказки Whisper ("ru", "en", и т.д.)
    """
    model = _get_model()

    print("[Transcriber] Распознаю речь...")
    result = model.transcribe(audio_path, language=language, **_TRANSCRIBE_OPTS)
    text = result["text"].strip()

    print(f"[Transcriber] Распознано: '{text}'")
    return text


def transcribe_diarized(
    loopback_path: str | None,
    mic_path: str | None,
    language: str = "ru",
    loopback_offset: float = 0.0,
    mic_offset: float = 0.0,
) -> str:
    """
    Транскрибирует два потока (loopback = собеседник, mic = вы) раздельно,
    объединяет сегменты по временным меткам и возвращает размеченный текст.

    Формат результата:
        **Собеседник:** текст...

        **Вы:** текст...

    Если доступен только один поток — транскрибирует его без разметки.
    """
    model = _get_model()

    def _transcribe_stream(path: str, speaker: str) -> list[dict]:
        print(f"[Transcriber] Распознаю поток '{speaker}'...")
        result = model.transcribe(path, language=language, **_TRANSCRIBE_OPTS)
        segments = [
            {
                "start": s["start"],
                "end": s["end"],
                "text": s["text"].strip(),
                "speaker": speaker,
            }
            for s in result.get("segments", [])
            if s["text"].strip()
        ]
        print(f"[Transcriber] '{speaker}': {len(segments)} сегментов.")
        return segments

    has_loopback = bool(loopback_path)
    has_mic = bool(mic_path)

    if not has_loopback and not has_mic:
        return "(речь не распознана)"

    # Если только один поток — простая транскрипция без разметки
    if has_loopback and not has_mic:
        segs = _transcribe_stream(loopback_path, "Собеседник")
        return " ".join(s["text"] for s in segs) or "(речь не распознана)"

    if has_mic and not has_loopback:
        segs = _transcribe_stream(mic_path, "Вы")
        return " ".join(s["text"] for s in segs) or "(речь не распознана)"

    # Оба потока — транскрибируем раздельно и объединяем по времени
    loopback_segs = _transcribe_stream(loopback_path, "Собеседник")
    mic_segs = _transcribe_stream(mic_path, "Вы")

    # Корректируем timestamps с учётом реального старта каждого потока
    for seg in loopback_segs:
        seg["start"] += loopback_offset
        seg["end"] += loopback_offset
    for seg in mic_segs:
        seg["start"] += mic_offset
        seg["end"] += mic_offset

    all_segs = sorted(loopback_segs + mic_segs, key=lambda s: s["start"])

    if not all_segs:
        return "(речь не распознана)"

    # Группируем подряд идущие реплики одного и того же спикера
    lines = []
    prev_speaker = None
    buffer: list[str] = []

    for seg in all_segs:
        if seg["speaker"] != prev_speaker:
            if buffer and prev_speaker:
                lines.append(f"**{prev_speaker}:** {' '.join(buffer)}")
            buffer = [seg["text"]]
            prev_speaker = seg["speaker"]
        else:
            buffer.append(seg["text"])

    if buffer and prev_speaker:
        lines.append(f"**{prev_speaker}:** {' '.join(buffer)}")

    return "\n\n".join(lines)
