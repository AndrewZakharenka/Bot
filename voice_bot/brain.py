"""
brain.py — генерация ответа через локальную LLM (Ollama).
Шаг 3 пайплайна: текст → ответ

Требует запущенного Ollama: https://ollama.com
Установка модели: ollama pull llama3.2

Если Ollama не запущена — бот отвечает заглушкой.
"""
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"  # можно заменить на "mistral", "gemma2" и т.д.

SYSTEM_PROMPT = (
    "Ты голосовой помощник. "
    "Отвечай коротко — не более двух предложений. "
    "Говори на русском языке."
)


def ask(user_text: str) -> str:
    """
    Отправляет текст в Ollama, возвращает ответ LLM.
    При ошибке соединения — возвращает сообщение об этом.
    """
    print(f"[Brain] Думаю над: '{user_text}'")

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": user_text,
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        answer = response.json()["response"].strip()
        print(f"[Brain] Ответ: '{answer}'")
        return answer

    except requests.exceptions.ConnectionError:
        msg = "Ollama не запущена. Открой терминал и выполни: ollama serve"
        print(f"[Brain] ОШИБКА: {msg}")
        return msg

    except requests.exceptions.Timeout:
        msg = "Ollama не ответила за 30 секунд."
        print(f"[Brain] ОШИБКА: {msg}")
        return msg

    except Exception as e:
        msg = f"Ошибка LLM: {e}"
        print(f"[Brain] ОШИБКА: {msg}")
        return msg
