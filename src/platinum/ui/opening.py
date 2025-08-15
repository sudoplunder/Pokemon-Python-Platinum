from .logo import show_logo, show_splash
from .typewriter import Typewriter


def show_opening(typewriter: Typewriter):
    """Display the game opening sequence"""
    show_logo()
    show_splash()
    
    typewriter.print("Press Enter to continue...")
    input()  # Wait for user
    
    print("\n" * 3)  # Clear screen effect