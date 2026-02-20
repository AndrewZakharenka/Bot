def get_bot_response(message, version, bot_name):
    if message.lower() == "стоп":
        print(format_message(bot_name, "До свидания!"))
        return False
    elif message.lower() == "помощь":
        print(format_message(bot_name, "Команды: стоп, помощь, версия"))
        return True
    elif message.lower() == "версия":
        print(format_message(bot_name, f"Версия приложения: {version}"))
        return True
    else:
        print(format_message(bot_name, f"Вы сказали: {message}"))
        return True


def format_message(sender, text):
    return f"{sender}: {text}"

# Функция 3: главный цикл
def run_bot(bot_name, version):  
    print(format_message(bot_name, "Привет! Я голосовой бот. Напиши 'помощь' для списка команд."))

    while True:
        message = input("Вы: ")
        if not get_bot_response(message, version, bot_name):
            return
    

if __name__ == "__main__":
    run_bot("A1 Bot", 1.0)