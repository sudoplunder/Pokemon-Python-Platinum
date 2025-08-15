"""
Main menu and options screens.
"""
from .input import choose_from_menu
from .typewriter import typewriter_effect


def show_main_menu(settings) -> str:
    """
    Show the main menu and return user choice.
    
    Args:
        settings: Settings object
        
    Returns:
        Choice string: 'new_game', 'continue', 'options', 'credits', 'quit'
    """
    print("\033[2J\033[H")  # Clear screen
    print("=" * 50)
    print("            MAIN MENU")
    print("=" * 50)
    print()
    
    options = [
        "New Game",
        "Continue Game",
        "Options",
        "Credits",
        "Quit"
    ]
    
    choice = choose_from_menu(options, "Select an option:")
    
    choice_map = {
        0: "new_game",
        1: "continue", 
        2: "options",
        3: "credits",
        4: "quit"
    }
    
    return choice_map[choice]


def show_options_menu(settings) -> bool:
    """
    Show the options menu.
    
    Args:
        settings: Settings object
        
    Returns:
        True if settings were changed, False otherwise
    """
    changed = False
    
    while True:
        print("\033[2J\033[H")  # Clear screen
        print("=" * 50)
        print("            OPTIONS")
        print("=" * 50)
        print()
        
        print(f"Text Speed: {settings.text_speed}")
        print(f"Sound: {'On' if settings.sound_enabled else 'Off'}")
        print(f"Dialogue Mode: {settings.dialogue_mode}")
        print()
        
        options = [
            "Change Text Speed",
            "Toggle Sound",
            "Change Dialogue Mode",
            "Reset to Defaults",
            "Back to Main Menu"
        ]
        
        choice = choose_from_menu(options, "Select an option:")
        
        if choice == 0:
            _change_text_speed(settings)
            changed = True
        elif choice == 1:
            settings.sound_enabled = not settings.sound_enabled
            changed = True
        elif choice == 2:
            _change_dialogue_mode(settings)
            changed = True
        elif choice == 3:
            settings.reset_to_defaults()
            changed = True
        elif choice == 4:
            break
    
    if changed:
        settings.save()
    
    return changed


def _change_text_speed(settings):
    """Change text speed setting."""
    speeds = ["Fast", "Normal", "Slow"]
    current_index = ["fast", "normal", "slow"].index(settings.text_speed)
    
    print(f"\nCurrent text speed: {speeds[current_index]}")
    choice = choose_from_menu(speeds, "Select text speed:")
    
    speed_map = {0: "fast", 1: "normal", 2: "slow"}
    settings.text_speed = speed_map[choice]


def _change_dialogue_mode(settings):
    """Change dialogue mode setting."""
    modes = ["Concise", "Expanded", "Alternate"]
    current_index = ["concise", "expanded", "alt"].index(settings.dialogue_mode)
    
    print(f"\nCurrent dialogue mode: {modes[current_index]}")
    print("\nConcise: Brief, direct text")
    print("Expanded: Rich, detailed descriptions")  
    print("Alternate: Random alternative phrasings")
    
    choice = choose_from_menu(modes, "Select dialogue mode:")
    
    mode_map = {0: "concise", 1: "expanded", 2: "alt"}
    settings.dialogue_mode = mode_map[choice]