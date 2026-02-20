# =============================================================
# День 4: Списки, словари, цикл for
# =============================================================
#
# ТЕОРИЯ — СПИСКИ
# Список — упорядоченная коллекция значений. Изменяема.
#
#   history = []            # пустой список
#   history.append("hi")   # добавить в конец → ["hi"]
#   history[0]             # первый элемент → "hi"
#   len(history)           # длина → 1
#
# ТЕОРИЯ — СЛОВАРИ
# Словарь — пары ключ: значение. Быстрый поиск по ключу.
#
#   commands = {
#       "помощь": "Команды: стоп, помощь, версия",
#       "версия": "v1.0",
#   }
#   commands["помощь"]      # → "Команды: стоп, помощь, версия"
#   "стоп" in commands      # → True / False
#
# ТЕОРИЯ — ЦИКЛ for
# Перебирает элементы любой последовательности.
#
#   for item in history:
#       print(item)
#
#   for key, value in commands.items():
#       print(key, "→", value)
#
# =============================================================


# --- Данные ---

BOT_NAME = "A1 Bot"
VERSION = "1.1"

# Команды теперь в словаре, а не в if/elif
# Ключ — команда, значение — текст ответа
COMMANDS = {
    "помощь": "Команды: стоп, помощь, версия, история, поиск",
    "версия": f"Версия приложения: {VERSION}",
    "история": None,  # обрабатывается отдельно (нужен список history)
}


# --- Функции ---

def format_message(sender, text):
    return f"{sender}: {text}"


def show_history(history):
    """Выводит всю историю диалога через цикл for."""
    if not history:
        print(format_message(BOT_NAME, "История пуста."))
        return

    print(format_message(BOT_NAME, "История диалога:"))
    for i, entry in enumerate(history, start=1):   # enumerate даёт индекс
        print(f"  {i}. {entry}")


def get_bot_response(message, history):
    """
    Обрабатывает сообщение пользователя.
    Возвращает True, чтобы продолжать цикл, или False — остановить бота.
    """
    cmd = message.lower().strip()
    print_message = ""

    if cmd == "стоп":
        print_message = format_message(BOT_NAME, "До свидания!")
        history.append(print_message)
        print(print_message)
        return False

    if cmd == "история":
        show_history(history)
        print(format_message(BOT_NAME, f"Количество сообщений: {len(history)}"))
        return True
    
    if cmd == "поиск":
        text = format_message(BOT_NAME, f"Введите слово по которому необходимо осуществить поиск")
        history.append(text)
        print(text)
        message = input("Вы: ")
        search_list = []
        for item in history:
            if message in item:
                search_list.append(item)

        show_history(search_list)
        return True

    if cmd in COMMANDS:
        # Ответ берём прямо из словаря — никаких if/elif
        response = COMMANDS[cmd]
        print_message = format_message(BOT_NAME, response)
        history.append(print_message)
        print(print_message)
        return True

    # Неизвестная команда
    response = f"Вы сказали: {message}"
    print_message = format_message(BOT_NAME, response)
    history.append(print_message)
    print(print_message)
    return True


def run_bot():
    history = []   # список для хранения истории диалога

    print(format_message(BOT_NAME, "Привет! Я голосовой бот. Напиши 'помощь' для списка команд."))
    history.append(format_message(BOT_NAME, "Привет! Я голосовой бот. Напиши 'помощь' для списка команд."))
    while True:
        message = input("Вы: ")

        # Сохраняем каждое сообщение пользователя в историю
        history.append(f"Вы: {message}")

        if not get_bot_response(message, history):
            break   # выходим из while


if __name__ == "__main__":
    run_bot()
