"""
ui.py — десктопный интерфейс Voice Bot.
Запуск: python voice_bot/ui.py

Две вкладки:
  🎤 Чат     — запись с микрофона → STT → LLM → TTS
  📋 Встречи — запись системного аудио → STT → МОМ → история
"""
import sys
import os
import threading
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import customtkinter as ctk
from voice_bot import recorder, transcriber, brain, speaker
from voice_bot.meeting_tab import MeetingTab

# ── Тема оформления ──────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

RECORD_SECONDS = 5


class VoiceBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Voice Bot A1")
        self.geometry("720x820")
        self.resizable(False, False)

        self._build_ui()

    # ── Построение интерфейса ─────────────────────────────────

    def _build_ui(self):
        # Заголовок
        header = ctk.CTkLabel(
            self, text="🎤  Voice Bot A1",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.pack(pady=(16, 8))

        # Статус (общий для обеих вкладок)
        self.status_label = ctk.CTkLabel(
            self,
            text="● Готов к записи",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        )
        self.status_label.pack(pady=(0, 6))

        # TabView
        self.tabs = ctk.CTkTabview(self, width=690, height=700)
        self.tabs.pack(padx=15, pady=(0, 12))

        self.tabs.add("🎤  Чат")
        self.tabs.add("📋  Встречи")

        self._build_chat_tab(self.tabs.tab("🎤  Чат"))
        self._build_meeting_tab(self.tabs.tab("📋  Встречи"))

        # Приветствие
        self._add_message("Бот", "Привет! Нажми кнопку и говори.")

    # ── Вкладка «Чат» ─────────────────────────────────────────

    def _build_chat_tab(self, tab):
        # Область чата
        self.chat = ctk.CTkTextbox(
            tab,
            width=660, height=540,
            font=ctk.CTkFont(size=14),
            wrap="word",
            state="normal",
        )
        self.chat.pack(padx=10, pady=(10, 8))

        # Теги цвета
        self.chat.tag_config("user", foreground="#64B5F6")
        self.chat.tag_config("bot",  foreground="#A5D6A7")
        self.chat.tag_config("info", foreground="#888888")

        # Read-only + копирование
        tb = self.chat._textbox
        tb.bind("<Key>", lambda e: "break")
        tb.bind("<Control-c>", lambda e: None)
        tb.bind("<Control-a>", lambda e: (
            tb.tag_add("sel", "1.0", "end"), "break"
        ))

        # Контекстное меню
        self._chat_menu = tk.Menu(self, tearoff=0)
        self._chat_menu.add_command(
            label="Копировать",
            command=lambda: tb.event_generate("<<Copy>>"),
        )
        self._chat_menu.add_command(
            label="Выделить всё",
            command=lambda: tb.tag_add("sel", "1.0", "end"),
        )
        self._chat_menu.add_separator()
        self._chat_menu.add_command(
            label="Очистить чат",
            command=lambda: self.chat.delete("1.0", "end"),
        )
        tb.bind("<Button-3>", lambda e: self._chat_menu.tk_popup(e.x_root, e.y_root))

        # Кнопка записи
        self.btn = ctk.CTkButton(
            tab,
            text=f"🎤  Говори  ({RECORD_SECONDS} сек)",
            width=260, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._on_record_click,
        )
        self.btn.pack(pady=(0, 10))

    # ── Вкладка «Встречи» ─────────────────────────────────────

    def _build_meeting_tab(self, tab):
        self._meeting_tab = MeetingTab(
            tab,
            set_status_cb=self._set_status,
            fg_color="transparent",
        )
        self._meeting_tab.pack(fill="both", expand=True)

    # ── Обработчик кнопки «Говори» ────────────────────────────

    def _on_record_click(self):
        self.btn.configure(state="disabled")
        thread = threading.Thread(target=self._pipeline, daemon=True)
        thread.start()

    # ── Пайплайн чата ────────────────────────────────────────

    def _pipeline(self):
        try:
            self._set_status("🔴  Запись...")
            audio_path = recorder.record(seconds=RECORD_SECONDS)

            self._set_status("⏳  Распознаю речь (Whisper)...")
            user_text = transcriber.transcribe(audio_path)
            recorder.delete(audio_path)

            if not user_text:
                self._add_message("info", "Ничего не услышал, попробуй ещё раз.")
                return

            self._add_message("Вы", user_text)

            self._set_status("💭  Думаю (Ollama)...")
            response = brain.ask(user_text)
            self._add_message("Бот", response)

            self._set_status("🔊  Говорю...")
            speaker.speak(response)

        except Exception as e:
            self._add_message("info", f"Ошибка: {e}")

        finally:
            self._set_status("● Готов к записи")
            self.after(0, lambda: self.btn.configure(state="normal"))

    # ── Thread-safe хелперы ───────────────────────────────────

    def _set_status(self, text: str):
        self.after(0, lambda: self.status_label.configure(text=text))

    def _add_message(self, sender: str, text: str):
        def _update():
            if sender == "Вы":
                self.chat.insert("end", f"Вы:   {text}\n\n", "user")
            elif sender == "Бот":
                self.chat.insert("end", f"Бот:  {text}\n\n", "bot")
            else:
                self.chat.insert("end", f"      {text}\n\n", "info")
            self.chat.see("end")
        self.after(0, _update)


# ── Точка входа ───────────────────────────────────────────────

if __name__ == "__main__":
    app = VoiceBotApp()
    app.mainloop()
