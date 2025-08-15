"""
High-level menus using the unified navigation system.
"""
from __future__ import annotations
from platinum.ui.menu_nav import select_menu

def main_menu() -> str:
    choice = select_menu(
        "MAIN MENU",
        [
            ("New Game", "new"),
            ("Options", "options"),
            ("View Flags (Debug)", "flags"),
            ("Quit", "quit")
        ]
    )
    # Esc returns None -> treat as Quit gracefully
    return choice or "quit"

def options_submenu(settings) -> None:
    while True:
        choice = select_menu(
            "OPTIONS",
            [
                (f"Dialogue Mode [{settings.data.dialogue_mode}]", "dialogue_mode"),
                (f"Text Speed [{settings.data.text_speed}]", "text_speed"),
                (f"Log Level [{settings.data.log_level}]", "log_level"),
                ("Return", "return")
            ],
            footer="↑/↓ or W/S • Enter to edit • Esc to return"
        )
        if choice in (None, "return"):
            return
        if choice == "dialogue_mode":
            _edit_dialogue_mode(settings)
        elif choice == "text_speed":
            _edit_text_speed(settings)
        elif choice == "log_level":
            _edit_log_level(settings)

def _edit_dialogue_mode(settings):
    choice = select_menu(
        "DIALOGUE MODE",
        [
            ("Concise", "concise"),
            ("Base", "base"),
            ("Expanded", "expanded"),
            ("Alt (random variant)", "alt"),
            ("Cancel", "cancel")
        ]
    )
    if choice and choice != "cancel":
        settings.data.dialogue_mode = choice
        settings.data.normalize()
        settings.save()

def _edit_text_speed(settings):
    choice = select_menu(
        "TEXT SPEED",
        [
            ("Fast (1)", "1"),
            ("Normal (2)", "2"),
            ("Slow (3)", "3"),
            ("Cancel", "cancel")
        ]
    )
    if choice and choice.isdigit():
        settings.data.text_speed = int(choice)
        settings.data.normalize()
        settings.save()

def _edit_log_level(settings):
    choice = select_menu(
        "LOG LEVEL",
        [
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARN", "WARN"),
            ("ERROR", "ERROR"),
            ("Cancel", "cancel")
        ]
    )
    if choice and choice in {"DEBUG","INFO","WARN","ERROR"}:
        from platinum.core.logging import logger
        settings.data.log_level = choice
        settings.data.normalize()
        logger.set_level(settings.data.log_level)
        settings.save()