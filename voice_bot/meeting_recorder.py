"""
meeting_recorder.py — запись системного аудио + микрофона (WASAPI loopback).

Два потока записываются параллельно и микшируются в один WAV-файл:
  - loopback: всё что играет на ПК (голос собеседника в Zoom/Meet/Teams)
  - микрофон: ваш голос

Публичные методы:
    start()          — начинает запись (в фоновом потоке)
    stop() -> path   — останавливает запись, возвращает путь к WAV-файлу
"""
import os
import wave
import tempfile
import threading
import time

import numpy as np
import scipy.signal

try:
    import pyaudiowpatch as pyaudio
    _WPATCH_AVAILABLE = True
except ImportError:
    import pyaudio
    _WPATCH_AVAILABLE = False


CHUNK = 1024
FORMAT = pyaudio.paInt16
TARGET_RATE = 44100
TARGET_CHANNELS = 2


def _find_loopback_device(pa):
    """Ищет WASAPI loopback-устройство (то, что играет на ПК)."""
    if not _WPATCH_AVAILABLE:
        return None
    try:
        wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        return None

    default_out_idx = wasapi_info.get("defaultOutputDevice", -1)
    if default_out_idx < 0:
        return None

    default_out = pa.get_device_info_by_index(default_out_idx)

    # pyaudiowpatch добавляет " [Loopback]" к имени — используем startswith
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if (
            dev.get("isLoopbackDevice", False)
            and dev["name"].startswith(default_out["name"])
        ):
            return dev

    # Фолбэк: первый попавшийся loopback
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if dev.get("isLoopbackDevice", False):
            return dev

    return None


def _bytes_to_array(raw: bytes, channels: int) -> np.ndarray:
    """bytes → numpy int16 array shape (samples, channels)."""
    arr = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        arr = arr.reshape(-1, channels)
    else:
        arr = arr.reshape(-1, 1)
    return arr


def _resample(arr: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Ресемплирует массив (samples, channels) с src_rate на dst_rate."""
    if src_rate == dst_rate:
        return arr
    n_samples = int(len(arr) * dst_rate / src_rate)
    resampled = np.zeros((n_samples, arr.shape[1]), dtype=np.float32)
    for ch in range(arr.shape[1]):
        resampled[:, ch] = scipy.signal.resample(arr[:, ch].astype(np.float32), n_samples)
    return resampled.astype(np.int16)


def _to_stereo(arr: np.ndarray) -> np.ndarray:
    """Моно (N,1) → стерео (N,2)."""
    if arr.shape[1] == 1:
        return np.column_stack([arr, arr])
    return arr


def _mix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Микширует два стерео-массива одинаковой длины (среднее, без клиппинга)."""
    min_len = min(len(a), len(b))
    a = a[:min_len].astype(np.int32)
    b = b[:min_len].astype(np.int32)
    mixed = ((a + b) // 2).astype(np.int16)
    return mixed


class MeetingRecorder:
    """Записывает системный звук + микрофон и сохраняет смешанный WAV."""

    def __init__(self):
        self._pa = None
        self._recording = False
        self._start_time: float = 0.0

        self._loopback_stream = None
        self._mic_stream = None
        self._loopback_frames: list[bytes] = []
        self._mic_frames: list[bytes] = []
        self._loopback_rate: int = TARGET_RATE
        self._loopback_channels: int = TARGET_CHANNELS
        self._mic_rate: int = TARGET_RATE

        self._loopback_thread: threading.Thread | None = None
        self._mic_thread: threading.Thread | None = None

    # ── Запуск ────────────────────────────────────────────────

    def start(self):
        if self._recording:
            return

        self._pa = pyaudio.PyAudio()
        self._loopback_frames = []
        self._mic_frames = []
        self._recording = True
        self._start_time = time.time()

        # — Loopback (системный звук) —
        loopback = _find_loopback_device(self._pa)
        if loopback:
            self._loopback_rate = int(loopback.get("defaultSampleRate", TARGET_RATE))
            self._loopback_channels = loopback.get("maxInputChannels", TARGET_CHANNELS)
            self._loopback_stream = self._pa.open(
                format=FORMAT,
                channels=self._loopback_channels,
                rate=self._loopback_rate,
                input=True,
                input_device_index=loopback["index"],
                frames_per_buffer=CHUNK,
            )
            self._loopback_thread = threading.Thread(
                target=self._record_loop,
                args=(self._loopback_stream, self._loopback_frames),
                daemon=True,
            )
            self._loopback_thread.start()
            print(f"[MeetingRecorder] Loopback: '{loopback['name']}' "
                  f"({self._loopback_channels}ch, {self._loopback_rate}Hz)")
        else:
            print("[MeetingRecorder] Loopback не найден — системный звук не будет записан.")

        # — Микрофон —
        try:
            mic_info = self._pa.get_default_input_device_info()
            self._mic_rate = int(mic_info.get("defaultSampleRate", TARGET_RATE))
            self._mic_stream = self._pa.open(
                format=FORMAT,
                channels=1,
                rate=self._mic_rate,
                input=True,
                frames_per_buffer=CHUNK,
            )
            self._mic_thread = threading.Thread(
                target=self._record_loop,
                args=(self._mic_stream, self._mic_frames),
                daemon=True,
            )
            self._mic_thread.start()
            print(f"[MeetingRecorder] Микрофон: '{mic_info['name']}' (1ch, {self._mic_rate}Hz)")
        except Exception as e:
            print(f"[MeetingRecorder] Микрофон недоступен: {e}")

        print("[MeetingRecorder] Запись началась.")

    def _record_loop(self, stream, frames: list):
        while self._recording:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            except Exception as e:
                print(f"[MeetingRecorder] Ошибка чтения: {e}")
                break

    # ── Остановка ─────────────────────────────────────────────

    def stop(self) -> str:
        if not self._recording:
            return ""

        self._recording = False
        duration = time.time() - self._start_time

        for t in (self._loopback_thread, self._mic_thread):
            if t:
                t.join(timeout=2)

        for s in (self._loopback_stream, self._mic_stream):
            if s:
                try:
                    s.stop_stream()
                    s.close()
                except Exception:
                    pass

        self._pa.terminate()

        # — Микширование —
        wav_path = self._mix_and_save()
        print(f"[MeetingRecorder] Запись остановлена ({duration:.1f} сек). Файл: {wav_path}")
        return wav_path

    def _mix_and_save(self) -> str:
        """Микширует loopback + микрофон и сохраняет WAV."""
        tmp = tempfile.mktemp(suffix=".wav")

        has_loopback = bool(self._loopback_frames)
        has_mic = bool(self._mic_frames)

        if not has_loopback and not has_mic:
            # Нечего сохранять — пустой файл
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(TARGET_CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(TARGET_RATE)
                wf.writeframes(b"")
            return tmp

        # Собираем loopback в массив
        if has_loopback:
            raw_lb = b"".join(self._loopback_frames)
            arr_lb = _bytes_to_array(raw_lb, self._loopback_channels)
            arr_lb = _resample(arr_lb, self._loopback_rate, TARGET_RATE)
            arr_lb = _to_stereo(arr_lb)

        # Собираем микрофон в массив
        if has_mic:
            raw_mic = b"".join(self._mic_frames)
            arr_mic = _bytes_to_array(raw_mic, 1)
            arr_mic = _resample(arr_mic, self._mic_rate, TARGET_RATE)
            arr_mic = _to_stereo(arr_mic)

        # Выбираем результат
        if has_loopback and has_mic:
            mixed = _mix(arr_lb, arr_mic)
        elif has_loopback:
            mixed = arr_lb
        else:
            mixed = arr_mic

        # Сохраняем
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(TARGET_CHANNELS)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(TARGET_RATE)
            wf.writeframes(mixed.tobytes())

        return tmp

    @property
    def elapsed_seconds(self) -> float:
        if not self._recording:
            return 0.0
        return time.time() - self._start_time
