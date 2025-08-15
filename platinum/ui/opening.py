"""
Opening sequence: credits, legal notices, and title screen.
"""
import time
from .typewriter import typewriter_lines
from .logo import show_colored_logo, show_simple_title
from .input import wait_for_key, choose_from_menu


def show_credits_sequence():
    """Display the opening credits and legal sequence."""
    print("\033[2J\033[H")  # Clear screen and move cursor to top
    
    credits = [
        "Pokémon Platinum - Python Edition",
        "",
        "A fan recreation project",
        "",
        "Original Pokémon Platinum © Nintendo/Game Freak/Creatures Inc.",
        "This is a non-commercial educational project.",
        "",
        "Programming: Community Contributors",
        "Based on the original Sinnoh region adventure",
        "",
        "Press any key to continue..."
    ]
    
    typewriter_lines(credits, line_delay=0.8, char_delay=0.02)
    wait_for_key()


def show_title_screen() -> str:
    """
    Display the title screen and return user choice.
    
    Returns:
        'main_menu' or 'quit'
    """
    print("\033[2J\033[H")  # Clear screen
    
    try:
        show_colored_logo()
    except:
        show_simple_title()
    
    print()
    print("Welcome to the world of Pokémon!")
    print()
    
    options = ["Start Game", "Quit"]
    choice = choose_from_menu(options, "What would you like to do?")
    
    if choice == 0:
        return "main_menu"
    else:
        return "quit"