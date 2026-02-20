"""
meeting_recorder.py — запись системного аудио + микрофона (WASAPI loopback).

Два потока записываются параллельно:
  - loopback: всё что играет на ПК (голос собеседника в Zoom/Meet/Teams)
  - микрофон: ваш голос

stop() возвращает dict {"loopback": path_or_None, "mic": path_or_None}
с WAV-файлами в 16 kHz mono — оптимальный формат для Whisper.
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
WHISPER_RATE = 16000   # Whisper нативно работает с 16 kHz mono
TARGET_RATE = 44100    # для внутренних вычислений loopback


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


def _resample_arr(arr: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Ресемплирует массив (samples, channels) с src_rate на dst_rate."""
    if src_rate == dst_rate:
        return arr
    n_samples = int(len(arr) * dst_rate / src_rate)
    resampled = np.zeros((n_samples, arr.shape[1]), dtype=np.float32)
    for ch in range(arr.shape[1]):
        resampled[:, ch] = scipy.signal.resample(arr[:, ch].astype(np.float32), n_samples)
    return resampled.astype(np.int16)


def _save_16k_mono(frames: list[bytes], src_rate: int, src_channels: int) -> str | None:
    """
    Конвертирует записанные фреймы в 16 kHz mono WAV (формат для Whisper).
    Нормализует громкость. Возвращает путь к временному файлу или None.
    """
    if not frames:
        return None

    raw = b"".join(frames)
    arr = _bytes_to_array(raw, src_channels)

    # Mono: усредняем каналы
    if arr.shape[1] > 1:
        arr = arr.mean(axis=1, keepdims=True).astype(np.int16)

    # Ресемплируем до 16 kHz
    arr = _resample_arr(arr, src_rate, WHISPER_RATE)

    # Нормализуем громкость (тихие сигналы усиливаем до 90% от макс)
    peak = np.abs(arr).max()
    if 0 < peak < 16000:
        arr = (arr.astype(np.float32) * (32767 / peak) * 0.9).astype(np.int16)

    tmp = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # int16 = 2 bytes
        wf.setframerate(WHISPER_RATE)
        wf.writeframes(arr.tobytes())

    return tmp


class MeetingRecorder:
    """Записывает системный звук + микрофон, сохраняет раздельные 16 kHz WAV."""

    def __init__(self):
        self._pa = None
        self._recording = False
        self._start_time: float = 0.0

        self._loopback_stream = None
        self._mic_stream = None
        self._loopback_frames: list[bytes] = []
        self._mic_frames: list[bytes] = []
        self._loopback_rate: int = TARGET_RATE
        self._loopback_channels: int = 2
        self._mic_rate: int = TARGET_RATE

        # Реальное смещение старта каждого потока от _start_time (сек)
        self._loopback_start_offset: float = 0.0
        self._mic_start_offset: float = 0.0

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
            self._loopback_channels = loopback.get("maxInputChannels", 2)
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
            self._loopback_start_offset = time.time() - self._start_time
            print(f"[MeetingRecorder] Loopback: '{loopback['name']}' "
                  f"({self._loopback_channels}ch, {self._loopback_rate}Hz, "
                  f"offset={self._loopback_start_offset:.3f}s)")
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
            self._mic_start_offset = time.time() - self._start_time
            print(f"[MeetingRecorder] Микрофон: '{mic_info['name']}' "
                  f"(1ch, {self._mic_rate}Hz, offset={self._mic_start_offset:.3f}s)")
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

    def stop(self) -> dict:
        """
        Останавливает запись.
        Возвращает dict {"loopback": path_or_None, "mic": path_or_None}
        с 16 kHz mono WAV-файлами, готовыми для Whisper.
        """
        if not self._recording:
            return {"loopback": None, "mic": None}

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

        # Сохраняем каждый поток отдельно в 16 kHz mono
        loopback_path = _save_16k_mono(
            self._loopback_frames, self._loopback_rate, self._loopback_channels
        )
        mic_path = _save_16k_mono(
            self._mic_frames, self._mic_rate, 1
        )

        print(
            f"[MeetingRecorder] Запись остановлена ({duration:.1f} сек). "
            f"Loopback: {loopback_path}, Mic: {mic_path}"
        )
        return {
            "loopback": loopback_path,
            "mic": mic_path,
            "loopback_offset": self._loopback_start_offset,
            "mic_offset": self._mic_start_offset,
        }

    @property
    def elapsed_seconds(self) -> float:
        if not self._recording:
            return 0.0
        return time.time() - self._start_time
