#!/usr/bin/env python3
"""
Pokémon Platinum - Python Edition

Main entry point that serves as a thin wrapper around the modular launcher.
This replaces the previous monolithic approach with a clean separation of concerns.

The actual game logic is now organized in the platinum package with:
- Dialogue system and event framework
- Modular UI components  
- Settings management
- Battle system integration points (placeholders for now)

To run: python main.py
"""

from platinum.cli import run

if __name__ == "__main__":
    run()