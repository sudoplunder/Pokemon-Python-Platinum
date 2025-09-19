
"""Game launcher - Disabled version without banners."""

# This file is currently disabled to remove startup banners
# If you need enhanced terminal features, run setup_requirements.py first

import os
import sys

def setup_terminal_environment():
    """Basic terminal setup without banners."""
    if os.name == 'nt':  # Windows
        # Enable ANSI color support
        os.system('color')
        # Set title
        os.system('title Pokemon Platinum')


def show_enhanced_title():
    """Disabled - no banner display."""
    pass


if __name__ == "__main__":
    print("Starting Pokemon Platinum...")
    
    # Setup terminal environment
    setup_terminal_environment()
    
    # Run the game
    try:
        from platinum.cli import run
        run()
    except ImportError as e:
        print(f"Error: Could not import game modules: {e}")
        print("Please run: python setup_requirements.py")
        sys.exit(1)