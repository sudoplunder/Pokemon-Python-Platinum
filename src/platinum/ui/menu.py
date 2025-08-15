from .input import get_choice


def show_main_menu() -> str:
    """Display main menu and return user choice"""
    print("=== MAIN MENU ===")
    print()
    
    choices = ["New Game", "Load Game", "Options", "Exit"]
    return get_choice("What would you like to do?", choices)


def show_options_menu() -> str:
    """Display options menu and return user choice"""
    print("=== OPTIONS ===")
    print()
    
    choices = ["Dialogue Mode", "Text Speed", "Back"]
    return get_choice("What would you like to configure?", choices)