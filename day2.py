def main():
    bot_name = "A1 Bot"

    print(f"{bot_name}: Привет! Я голосовой бот. Напиши 'помощь' для списка команд.")

    while True:
        message = input("Вы: ")

        if message.lower() == "стоп":
            print(f"{bot_name}: До свидания!")
            break
        elif message.lower() == "помощь":
            print(f"{bot_name}: Команды: стоп, помощь")
        else:
            print(f"{bot_name}: Вы сказали: {message}")


if __name__ == "__main__":
    main()