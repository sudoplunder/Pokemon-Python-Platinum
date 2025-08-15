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
            ("Continue", "continue"),
            ("Overworld (Active Session)", "overworld"),
            ("Save (In-Session)", "save"),
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
                (f"Text Speed [{settings.data.text_speed}]", "text_speed"),
                (f"Log Level [{settings.data.log_level}]", "log_level"),
                ("Return", "return")
            ],
            footer="↑/↓ or W/S • Enter to edit • Esc to return"
        )
        if choice in (None, "return"):
            return
        if choice == "text_speed":
            _edit_text_speed(settings)
        elif choice == "log_level":
            _edit_log_level(settings)

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
        lvl: str = settings.data.log_level
        if lvl in {"DEBUG","INFO","WARN","ERROR"}:
            logger.set_level(lvl)  # type: ignore[arg-type]
        settings.save()