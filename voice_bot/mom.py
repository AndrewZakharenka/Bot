"""
mom.py — генерация МОМ (Minutes of Meeting) через Ollama.

Принимает транскрипцию встречи, возвращает структурированные итоги.
"""
from voice_bot import brain

_MOM_PROMPT = """Ты — ассистент для встреч. Тебе дана транскрипция встречи.
Составь краткие итоги встречи на русском языке в следующем формате:

## Темы обсуждения
- ...

## Принятые решения
- ...

## Задачи и ответственные
- ...

## Следующие шаги
- ...

Транскрипция встречи:
{transcript}
"""


def generate(transcript: str) -> str:
    """
    Генерирует МОМ по транскрипции.

    transcript — распознанный текст встречи
    Возвращает отформатированный текст МОМ.
    """
    if not transcript.strip():
        return "Транскрипция пустая — МОМ не сгенерирован."

    prompt = _MOM_PROMPT.format(transcript=transcript)
    print("[MOM] Генерирую итоги встречи через Ollama...")
    result = brain.ask(prompt)
    print("[MOM] Готово.")
    return result
