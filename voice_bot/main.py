"""
main.py — главный файл Voice Bot.
Запуск: python voice_bot/main.py

Пайплайн:
  1. Нажми Enter
  2. Говори в микрофон (5 секунд)
  3. Whisper распознаёт речь → текст
  4. Ollama генерирует ответ → текст
  5. pyttsx3 произносит ответ вслух
"""
import sys
import os

# Позволяет запускать файл напрямую: python voice_bot/main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from voice_bot import recorder, transcriber, brain, speaker

RECORD_SECONDS = 5  # сколько секунд записывать голос


def run():
    print("=" * 45)
    print("         Voice Bot (локальный стек)")
    print("  Micro → Whisper → Ollama → pyttsx3")
    print("=" * 45)
    print("Нажми Enter чтобы говорить, Ctrl+C — выход.\n")

    while True:
        try:
            input("[ Enter → говори ]  ")
        except (KeyboardInterrupt, EOFError):
            print("\nВыход.")
            break

        # ── Шаг 1: Запись ──────────────────────────────
        audio_path = recorder.record(seconds=RECORD_SECONDS)

        # ── Шаг 2: Распознавание речи (STT) ────────────
        user_text = transcriber.transcribe(audio_path)
        recorder.delete(audio_path)  # удаляем временный WAV

        if not user_text:
            print("[ Бот ] Ничего не услышал, попробуй ещё раз.\n")
            continue

        print(f"\nВы сказали: {user_text}")

        # ── Шаг 3: Генерация ответа (LLM) ──────────────
        response = brain.ask(user_text)

        print(f"Бот ответил: {response}\n")

        # ── Шаг 4: Озвучка ответа (TTS) ────────────────
        speaker.speak(response)


if __name__ == "__main__":
    run()
