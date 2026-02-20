def main():
    name = "A1 Bot"
    version = 1.0       # число, не строка
    is_active = True

    # Красивая карточка
    print("=== Voice Bot Info ===")
    print(f"Имя:     {name}")
    print(f"Версия:  {version}")
    print(f"Статус:  {'активен' if is_active else 'неактивен'}")

    # Проверка типов
    print("\n=== Типы переменных ===")
    print(f"name — str: {isinstance(name, str)}")
    print(f"version — float: {isinstance(version, float)}")
    print(f"is_active — bool: {isinstance(is_active, bool)}")

if __name__ == "__main__":
    main()