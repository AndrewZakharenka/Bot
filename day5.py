# =============================================================
# День 5: Обработка ошибок — try/except
# =============================================================
#
# ТЕОРИЯ — ЗАЧЕМ
# Программа падает когда происходит что-то неожиданное.
# try/except позволяет поймать ошибку и продолжить работу.
#
#   try:
#       результат = 10 / 0          # ZeroDivisionError
#   except ZeroDivisionError:
#       print("Делить на ноль нельзя")
#
# ТЕОРИЯ — СТРУКТУРА
#
#   try:
#       # код который может сломаться
#   except КонкретнаяОшибка:
#       # что делать если эта ошибка случилась
#   except (ОшибкаА, ОшибкаБ):
#       # несколько типов сразу
#   except Exception as e:
#       # любая ошибка; e — объект с описанием
#       print(f"Ошибка: {e}")
#   else:
#       # выполняется если ошибок НЕ было
#   finally:
#       # выполняется ВСЕГДА (и при ошибке, и без)
#
# ТЕОРИЯ — ЧАСТЫЕ ТИПЫ ОШИБОК
#
#   ValueError        — неверное значение  (int("abc"))
#   TypeError         — неверный тип       (1 + "a")
#   KeyError          — нет ключа в словаре (d["x"] если x не существует)
#   IndexError        — нет индекса в списке (lst[99] если меньше 99 элементов)
#   FileNotFoundError — файл не найден
#   ZeroDivisionError — деление на ноль
#
# =============================================================


BOT_NAME = "A1 Bot"
VERSION = "1.2"

COMMANDS = {
    "помощь":  "Команды: стоп, помощь, версия, история, поиск, возраст",
    "версия":  f"Версия приложения: {VERSION}",
}


# --- Вспомогательные функции ---

def format_message(sender, text):
    return f"{sender}: {text}"


def show_history(history):
    if not history:
        print(format_message(BOT_NAME, "История пуста."))
        return
    print(format_message(BOT_NAME, "История диалога:"))
    for i, entry in enumerate(history, start=1):
        print(f"  {i}. {entry}")


# --- Новые функции с обработкой ошибок ---

def ask_age():
    """
    Просит пользователя ввести возраст.
    Повторяет запрос если введено не число.
    Демонстрирует: ValueError, цикл с try/except.
    """
    while True:
        raw = input("Ваш возраст: ")
        try:
            age = int(raw)          # упадёт ValueError если raw — не число
            if age <= 0 or age > 150:
                print(format_message(BOT_NAME, "Возраст должен быть от 1 до 150."))
                continue
            return age
        except ValueError:
            print(format_message(BOT_NAME, f"'{raw}' — это не число. Попробуй ещё раз."))


def get_from_history(history, index):
    """
    Возвращает запись из истории по номеру (1-based).
    Демонстрирует: IndexError, ValueError.
    """
    try:
        i = int(index)          # ValueError если не число
        return history[i - 1]  # IndexError если выходит за границы
    except ValueError:
        return f"'{index}' — не число."
    except IndexError:
        return f"Записи с номером {index} нет. Всего записей: {len(history)}."


# --- Основной обработчик ---

def get_bot_response(message, history):
    cmd = message.lower().strip()

    if cmd == "стоп":
        msg = format_message(BOT_NAME, "До свидания!")
        history.append(msg)
        print(msg)
        return False

    if cmd == "история":
        show_history(history)
        print(format_message(BOT_NAME, f"Количество сообщений: {len(history)}"))
        return True

    if cmd == "поиск":
        prompt = format_message(BOT_NAME, "Введите слово для поиска:")
        history.append(prompt)
        print(prompt)
        word = input("Вы: ")
        results = [item for item in history if word.lower() in item.lower()]
        show_history(results)
        return True

    if cmd == "возраст":
        # команда демонстрирует try/except на практике
        age = ask_age()
        msg = format_message(BOT_NAME, f"Тебе {age} лет. Понял, запомнил!")
        history.append(msg)
        print(msg)
        return True

    if cmd.startswith("запись "):
        # "запись 3" → показать 3-ю запись истории
        # Демонстрирует ValueError + IndexError
        index = cmd.split(" ", 1)[1]    # всё после "запись "
        result = get_from_history(history, index)
        print(format_message(BOT_NAME, result))
        return True

    if cmd in COMMANDS:
        response = COMMANDS[cmd]
        msg = format_message(BOT_NAME, response)
        history.append(msg)
        print(msg)
        return True

    response = f"Вы сказали: {message}"
    msg = format_message(BOT_NAME, response)
    history.append(msg)
    print(msg)
    return True


def run_bot():
    history = []
    greeting = format_message(BOT_NAME, "Привет! Напиши 'помощь' для списка команд.")
    history.append(greeting)
    print(greeting)

    while True:
        try:
            message = input("Вы: ")
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C или Ctrl+D — вежливый выход
            print()
            print(format_message(BOT_NAME, "Сеанс прерван. До свидания!"))
            break

        history.append(f"Вы: {message}")

        if not get_bot_response(message, history):
            break


if __name__ == "__main__":
    run_bot()
