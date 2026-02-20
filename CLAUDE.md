# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**Prerequisites — must be running before launch:**
```bash
# 1. Start Ollama server (in a separate terminal)
C:/Users/Андрей/AppData/Local/Programs/Ollama/ollama.exe serve

# 2. Launch the UI
C:/Users/Андрей/AppData/Local/Programs/Python/Python313/python.exe voice_bot/ui.py
```

`python` / `python3` are not in the bash PATH. Always use the full path:
```
C:/Users/Андрей/AppData/Local/Programs/Python/Python313/python.exe
```

To run with a visible window from bash, use PowerShell:
```bash
powershell.exe -Command "Start-Process 'C:\Users\Андрей\AppData\Local\Programs\Python\Python313\python.exe' -ArgumentList 'voice_bot/ui.py' -WorkingDirectory 'C:\Users\Андрей\Bot' -WindowStyle Normal"
```

**Install dependencies:**
```bash
C:/Users/Андрей/AppData/Local/Programs/Python/Python313/python.exe -m pip install -r requirements.txt
C:/Users/Андрей/AppData/Local/Programs/Python/Python313/python.exe -m pip install pyaudiowpatch
```

**Install/update Ollama model:**
```bash
C:/Users/Андрей/AppData/Local/Programs/Ollama/ollama.exe pull llama3.2
```

## Architecture

Two independent modes share the same window via `CTkTabview`:

### Tab 1 — Chat (`voice_bot/ui.py` + pipeline modules)
Fixed-duration mic recording → Whisper STT → Ollama LLM → gTTS playback.
Pipeline runs in a `threading.Thread(daemon=True)`; UI updates go through `self.after(0, callback)`.

### Tab 2 — Meetings (`voice_bot/meeting_tab.py`)
Records system audio (WASAPI loopback) **and** microphone simultaneously in two parallel threads → stops on button click → transcribes via Whisper → generates MOM via Ollama → saves to `meetings/`.

## Module responsibilities

| Module | Role |
|---|---|
| `voice_bot/recorder.py` | Mic → WAV via `sounddevice` (16 kHz mono, for Whisper) |
| `voice_bot/transcriber.py` | WAV → text via `openai-whisper` model `small` |
| `voice_bot/brain.py` | text → LLM response via Ollama REST API (`llama3.2`) |
| `voice_bot/speaker.py` | text → audio via gTTS + pygame; pyttsx3 as offline fallback |
| `voice_bot/meeting_recorder.py` | Dual-stream: WASAPI loopback + mic, mixed to WAV with numpy |
| `voice_bot/mom.py` | Sends transcript to `brain.ask()` with structured MOM prompt |
| `voice_bot/history.py` | Saves/loads meetings as JSON in `meetings/` |
| `voice_bot/meeting_tab.py` | CTkFrame widget for the Meetings tab |
| `voice_bot/ui.py` | App entry point, builds CTkTabview with both tabs |

## Key implementation details

**ffmpeg workaround** (`transcriber.py`): `imageio-ffmpeg` ships a binary named `ffmpeg-win-x86_64-vX.Y.exe`. At import time, it's copied to `ffmpeg.exe` in the same dir and that dir is prepended to `PATH`. This must happen before Whisper is used.

**WASAPI loopback detection** (`meeting_recorder.py`): `pyaudiowpatch` appends `" [Loopback]"` to device names. Detection uses `dev["name"].startswith(default_out["name"])`, not exact equality. Falls back to first available loopback if no name match.

**Audio mixing**: Loopback (2ch, 44100 Hz) and mic (1ch, variable rate) are resampled via `scipy.signal.resample` to `TARGET_RATE=44100`, mono is expanded to stereo, then averaged with `(a + b) // 2` as int32 to avoid clipping.

**Ollama API**: `brain.py` calls `POST http://localhost:11434/api/generate` with `stream: false`, 30 s timeout. Returns stub message on `ConnectionError` or `Timeout` instead of raising.

**Thread-safe UI**: All UI mutations from worker threads must go through `self.after(0, lambda: ...)`.

## Learning exercises

`day1.py` – `day5.py` in the root are standalone Python learning exercises (variables, conditions, loops, functions, lists/dicts, try/except). Not part of the voice bot.
