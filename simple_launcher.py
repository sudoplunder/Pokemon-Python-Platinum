"""Simple launcher - Disabled version without banners."""

# This file is currently disabled to remove startup banners
# If you need enhanced terminal features, run setup_requirements.py first

import os
import sys

def setup_rich_terminal():
    """Basic terminal setup without banners."""
    if os.name == 'nt':
        os.system('color')
        os.system('title Pokemon Platinum')

if __name__ == "__main__":
    print("Starting Pokemon Platinum...")
    
    setup_rich_terminal()
    
    try:
        from platinum.cli import run
        run()
    except ImportError as e:
        print(f"Error: Could not import game modules: {e}")
        print("Please run: python setup_requirements.py")
        sys.exit(1)