from __future__ import annotations

def main_menu() -> str:
    print("\nMain Menu")
    print("  1) New Game")
    print("  2) Options")
    print("  3) Flags (debug)")
    print("  4) Quit")
    while True:
        c = input("> ").strip()
        if c == "1": return "new"
        if c == "2": return "options"
        if c == "3": return "flags"
        if c == "4": return "quit"
        print("Invalid.")