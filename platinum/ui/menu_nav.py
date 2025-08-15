"""
Generic vertical (and future horizontal) menu navigation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Callable
from platinum.ui.keys import read_key, Key
import shutil
import sys

try:
    from colorama import Fore, Style
except Exception:
    class _Dummy:
        RESET_ALL = ""
    class _F:
        CYAN = GREEN = YELLOW = MAGENTA = WHITE = ""
    Style = _Dummy()
    Fore = _F()

PointerStyle = Fore.YELLOW
HighlightStyle = Fore.CYAN
DimStyle = Fore.WHITE
Reset = getattr(Style, "RESET_ALL", "")

@dataclass
class MenuItem:
    label: str
    value: str
    disabled: bool = False
    help_text: Optional[str] = None

class Menu:
    def __init__(
        self,
        title: str,
        items: Sequence[MenuItem],
        allow_escape: bool = True,
        footer: str | None = "↑/↓ or W/S to move • Enter to select • Esc to cancel"
    ):
        self.title = title
        self.items = list(items)
        self.allow_escape = allow_escape
        self.footer = footer
        self.index = 0
        # Make sure starting selection isn't disabled
        if self.items and self.items[self.index].disabled:
            self._advance(1)

    def _advance(self, delta: int):
        if not self.items:
            return
        attempts = 0
        n = len(self.items)
        while attempts < n:
            self.index = (self.index + delta) % n
            if not self.items[self.index].disabled:
                return
            attempts += 1

    def _clear_screen(self):
        # Minimal flicker-friendly redraw (could optimize)
        print("\033[2J\033[H", end="")

    def _render(self):
        cols = shutil.get_terminal_size((80, 20)).columns
        print(self.title.center(cols))
        print("-" * min(cols, len(self.title) + 10))
        for i, item in enumerate(self.items):
            prefix = ">" if i == self.index else " "
            style = PointerStyle if i == self.index else DimStyle
            label = item.label
            if item.disabled:
                label = f"[X] {label}"
            print(f"{style}{prefix} {label}{Reset}")
        if self.footer:
            print()
            print(self.footer)
        cur = self.items[self.index]
        if cur.help_text:
            print()
            print(f"{HighlightStyle}{cur.help_text}{Reset}")

    def run(self) -> Optional[str]:
        while True:
            self._clear_screen()
            self._render()
            ev = read_key()
            if ev.key == Key.UP:
                self._advance(-1)
            elif ev.key == Key.DOWN:
                self._advance(1)
            elif ev.key == Key.ENTER:
                return self.items[self.index].value
            elif ev.key == Key.ESC and self.allow_escape:
                return None
            # ignore others

def select_menu(
    title: str,
    options: list[tuple[str, str]],
    footer: str | None = None
) -> str | None:
    items = [MenuItem(label=o[0], value=o[1]) for o in options]
    return Menu(title, items, allow_escape=True, footer=footer).run()