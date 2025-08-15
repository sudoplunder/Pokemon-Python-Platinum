"""
Non-blocking input utilities and menu choice helpers.
"""
import sys
import select
import tty
import termios
from typing import List, Optional


def get_key_press() -> Optional[str]:
    """
    Get a single key press without blocking.
    Returns None if no key is pressed.
    """
    if sys.stdin.isatty():
        try:
            # Check if input is available
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                # Save terminal settings
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())
                    key = sys.stdin.read(1)
                    return key
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass
    return None


def wait_for_key() -> str:
    """
    Wait for a key press and return it.
    """
    if sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                key = sys.stdin.read(1)
                return key
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except:
            pass
    
    # Fallback to standard input
    return input().lower() or 'enter'


def choose_from_menu(options: List[str], prompt: str = "Choose an option:") -> int:
    """
    Display a menu and get user choice.
    
    Args:
        options: List of menu options
        prompt: Prompt to display
        
    Returns:
        Index of chosen option (0-based)
    """
    while True:
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        
        try:
            choice = input("\nEnter choice: ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num - 1
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")