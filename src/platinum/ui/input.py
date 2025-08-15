def get_input(prompt: str = "> ") -> str:
    """Get user input with prompt"""
    return input(prompt).strip()


def get_choice(prompt: str, choices: list, default: str = None) -> str:
    """Get a choice from user with validation"""
    while True:
        print(prompt)
        for i, choice in enumerate(choices, 1):
            print(f"{i}. {choice}")
        
        response = get_input("Choose (number or name): ").lower()
        
        # Try to match by number
        try:
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        
        # Try to match by name
        for choice in choices:
            if response == choice.lower():
                return choice
        
        # Try partial match
        matches = [c for c in choices if c.lower().startswith(response)]
        if len(matches) == 1:
            return matches[0]
        
        if default and response == "":
            return default
        
        print("Invalid choice. Please try again.")


def confirm(prompt: str, default: bool = None) -> bool:
    """Get yes/no confirmation from user"""
    suffix = " (y/n): "
    if default is True:
        suffix = " (Y/n): "
    elif default is False:
        suffix = " (y/N): "
    
    while True:
        response = get_input(prompt + suffix).lower()
        
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response == "" and default is not None:
            return default
        
        print("Please enter 'y' or 'n'.")