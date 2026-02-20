"""
meeting_tab.py — вкладка "📋 Встречи" в UI Voice Bot.

Функционал:
- Кнопка старт/стоп записи системного аудио
- Таймер записи
- История встреч (кнопки по одной на встречу)
- Текстовые поля: транскрипция и МОМ (read-only + копирование)
"""
import os
import threading
import tkinter as tk

import customtkinter as ctk

from voice_bot import transcriber, mom as mom_module, history
from voice_bot.meeting_recorder import MeetingRecorder


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class MeetingTab(ctk.CTkFrame):
    """CTkFrame для вкладки встреч."""

    def __init__(self, parent, set_status_cb=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._set_status = set_status_cb or (lambda t: None)
        self._recorder = MeetingRecorder()
        self._recording = False
        self._timer_job = None
        self._history_buttons: list[ctk.CTkButton] = []

        self._build()
        self._load_history()

    # ── Построение интерфейса ─────────────────────────────────

    def _build(self):
        # ── Верхняя панель: кнопка + таймер ──────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 4))

        self.rec_btn = ctk.CTkButton(
            top,
            text="🔴  Начать запись",
            width=200, height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_rec_click,
        )
        self.rec_btn.pack(side="left")

        self.timer_label = ctk.CTkLabel(
            top,
            text="",
            font=ctk.CTkFont(size=15),
            text_color="#888888",
        )
        self.timer_label.pack(side="left", padx=(16, 0))

        # ── История встреч ────────────────────────────────────
        ctk.CTkLabel(
            self, text="История встреч",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#aaaaaa",
        ).pack(anchor="w", padx=16, pady=(8, 2))

        self.history_frame = ctk.CTkScrollableFrame(
            self, height=100, fg_color="#1e1e2e",
        )
        self.history_frame.pack(fill="x", padx=16, pady=(0, 8))

        # ── Транскрипция ──────────────────────────────────────
        ctk.CTkLabel(
            self, text="Транскрипция",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#aaaaaa",
        ).pack(anchor="w", padx=16, pady=(4, 2))

        self.transcript_box = self._make_textbox(height=160)
        self.transcript_box.pack(fill="x", padx=16, pady=(0, 8))

        # ── МОМ ───────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="МОМ — итоги встречи",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#aaaaaa",
        ).pack(anchor="w", padx=16, pady=(4, 2))

        # fill="both" + expand=True — блок растягивается вместе с окном
        self.mom_box = self._make_textbox(height=380)
        self.mom_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _make_textbox(self, height: int) -> ctk.CTkTextbox:
        """Создаёт read-only текстовое поле с поддержкой копирования."""
        box = ctk.CTkTextbox(
            self,
            height=height,
            font=ctk.CTkFont(size=13),
            wrap="word",
            state="normal",
        )
        tb = box._textbox
        tb.bind("<Key>", lambda e: "break")
        tb.bind("<Control-c>", lambda e: None)
        tb.bind("<Control-a>", lambda e: (
            tb.tag_add("sel", "1.0", "end"), "break"
        ))
        # Контекстное меню
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Копировать",
                         command=lambda b=tb: b.event_generate("<<Copy>>"))
        menu.add_command(label="Выделить всё",
                         command=lambda b=tb: b.tag_add("sel", "1.0", "end"))
        tb.bind("<Button-3>", lambda e, m=menu: m.tk_popup(e.x_root, e.y_root))
        return box

    # ── История ───────────────────────────────────────────────

    def _load_history(self):
        """Загружает кнопки истории встреч."""
        for btn in self._history_buttons:
            btn.destroy()
        self._history_buttons.clear()

        meetings = history.load_all()
        if not meetings:
            lbl = ctk.CTkLabel(
                self.history_frame,
                text="Встреч пока нет.",
                text_color="#666666",
                font=ctk.CTkFont(size=12),
            )
            lbl.pack(anchor="w", padx=8, pady=4)
            self._history_buttons.append(lbl)
            return

        for m in meetings:
            label = f"{m['date']}  ({_fmt_duration(m['duration_sec'])})"
            btn = ctk.CTkButton(
                self.history_frame,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=12),
                fg_color="#2a2a3e",
                hover_color="#3a3a5e",
                command=lambda data=m: self._show_meeting(data),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self._history_buttons.append(btn)

    def _show_meeting(self, data: dict):
        """Показывает транскрипцию и МОМ выбранной встречи."""
        self._set_text(self.transcript_box, data.get("transcript", ""))
        self._set_text(self.mom_box, data.get("mom", ""))

    # ── Запись ────────────────────────────────────────────────

    def _on_rec_click(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._recording = True
        self.rec_btn.configure(text="⏹  Стоп")
        self._recorder.start()
        self._tick_timer()
        self._set_status("🔴  Идёт запись встречи...")
        print("[MeetingTab] Запись встречи начата.")

    def _stop_recording(self):
        self._recording = False
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self.timer_label.configure(text="")
        self.rec_btn.configure(state="disabled", text="⏳  Обрабатываю...")
        self._set_status("⏳  Обрабатываю встречу...")

        duration = self._recorder.elapsed_seconds
        thread = threading.Thread(
            target=self._process_recording,
            args=(duration,),
            daemon=True,
        )
        thread.start()

    def _tick_timer(self):
        if not self._recording:
            return
        elapsed = self._recorder.elapsed_seconds
        self.timer_label.configure(text=_fmt_duration(elapsed))
        self._timer_job = self.after(1000, self._tick_timer)

    def _process_recording(self, duration: float):
        """Выполняется в worker-потоке: стоп → транскрипция → МОМ → сохранение."""
        paths: dict[str, str | None] = {}
        try:
            # Стоп записи — получаем dict {"loopback": path, "mic": path}
            paths = self._recorder.stop()

            # Транскрипция с разделением по собеседникам
            self._set_status("⏳  Транскрибирую (Whisper)...")
            transcript = transcriber.transcribe_diarized(
                paths.get("loopback"),
                paths.get("mic"),
                loopback_offset=paths.get("loopback_offset", 0.0),
                mic_offset=paths.get("mic_offset", 0.0),
            )

            self.after(0, lambda: self._set_text(self.transcript_box, transcript))

            # МОМ
            self._set_status("💭  Генерирую МОМ (Ollama)...")
            mom_text = mom_module.generate(transcript)
            self.after(0, lambda: self._set_text(self.mom_box, mom_text))

            # Сохранение
            history.save(transcript, mom_text, duration)

            # Обновить историю в UI
            self.after(0, self._load_history)
            self._set_status("✅  Встреча обработана.")

        except Exception as e:
            self._set_status(f"Ошибка: {e}")
            print(f"[MeetingTab] Ошибка: {e}")

        finally:
            # Удаляем временные WAV-файлы
            for p in paths.values():
                if p:
                    try:
                        os.remove(p)
                    except Exception:
                        pass

            self.after(0, lambda: self.rec_btn.configure(
                state="normal", text="🔴  Начать запись"
            ))

    # ── Хелперы ──────────────────────────────────────────────

    def _set_text(self, box: ctk.CTkTextbox, text: str):
        """Заменяет содержимое textbox (вызывать из main thread)."""
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.see("1.0")
