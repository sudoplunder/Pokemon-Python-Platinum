def menu_prompt(prompt: str, options: dict[str, str]) -> str:
    print(prompt)
    for key, label in options.items():
        print(f"  {key}) {label}")
    while True:
        choice = input("> ").strip().lower()
        if choice in options:
            return choice
        print("Invalid choice.")