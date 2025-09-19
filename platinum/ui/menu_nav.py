"""
Beautiful vertical menu navigation using Rich for stunning visuals.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Callable
from platinum.ui.keys import read_key, Key
import shutil
import sys

# Rich imports for beautiful menus
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.box import ROUNDED
from rich import print as rprint

# Global Rich console for menus
menu_console = Console()

def get_menu_color():
    """Get the current menu color from settings."""
    try:
        from platinum.system.settings import Settings
        settings = Settings.load()
        return settings.data.menu_color
    except:
        return "bright_white"  # fallback

# Rich styling for menus - will be dynamically updated
PointerStyle = "[bright_white]"
HighlightStyle = "[bright_white]"
DimStyle = "[bright_white]"
Reset = "[/]"

@dataclass
class MenuItem:
    label: str
    value: str
    disabled: bool = False
    help_text: Optional[str] = None
    # Optional ANSI color for the label text (e.g., Fore.GREEN). If set, label
    # will render in this color regardless of selection state.
    label_color: Optional[str] = None

class Menu:
    def __init__(
        self,
        title: str,
        items: Sequence[MenuItem],
        allow_escape: bool = True,
        footer: str | None = "↑/↓ or W/S to move • Enter to select • Esc to cancel",
        after_render: Optional[Callable[[], None]] = None,
        full_render: Optional[Callable[[], None]] = None,
    ):
        self.title = title
        self.items = list(items)
        self.allow_escape = allow_escape
        self.footer = footer
        self.index = 0
        self.after_render = after_render
        self.full_render = full_render
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
        menu_console.clear()

    def _render(self):
        # If a full_render callback is provided, use that instead
        if self.full_render:
            self.full_render()
            return
            
        # Get current menu color from settings
        menu_color = get_menu_color()
        
        # Create beautiful Rich-powered menu
        menu_table = Table(
            title=f"[bold {menu_color}]{self.title}[/bold {menu_color}]",
            box=ROUNDED,
            show_header=False,
            style="bright_white",
            title_style=f"bold {menu_color}",
            width=60
        )
        
        menu_table.add_column("Option", style="bright_white", justify="left")
        
        for i, item in enumerate(self.items):
            # Create styled menu item with very clear pointer
            if i == self.index:
                if item.disabled:
                    style_open, style_close = "[dim red]", "[/dim red]"
                    prefix = f"[{menu_color}]►[/{menu_color}] "  # Clear arrow
                else:
                    style_open, style_close = f"[{menu_color}]", f"[/{menu_color}]"
                    prefix = f"[{menu_color}]►[/{menu_color}] "  # Clear arrow
            else:
                if item.disabled:
                    style_open, style_close = "[dim]", "[/dim]"
                    prefix = "  "
                else:
                    style_open, style_close = "[bright_white]", "[/bright_white]"
                    prefix = "  "
            
            label = f"[X] {item.label}" if item.disabled else item.label
            
            # Use custom color if provided
            if item.label_color:
                full_label = f"{prefix}{item.label_color}{label}[/]"
            else:
                full_label = f"{prefix}{style_open}{label}{style_close}"
            
            menu_table.add_row(full_label)
        
        # Display the menu
        menu_console.print(Align.center(menu_table))
        
        # Help text for current item
        cur = self.items[self.index] if self.items else None
        if cur and cur.help_text:
            help_panel = Panel(
                cur.help_text,
                style="bright_white",
                box=ROUNDED,
                title=f"[bold {menu_color}]Info[/bold {menu_color}]"
            )
            menu_console.print(help_panel)
        
        # Footer
        if self.footer:
            footer_panel = Panel(
                self.footer,
                style="dim bright_white",
                box=ROUNDED
            )
            menu_console.print(footer_panel)
        
        # Optional hook to render extra UI (e.g., battle HUD) under the menu
        if self.after_render:
            menu_console.print()
            self.after_render()

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
            elif ev.key == Key.B:
                return "__b__"
            elif ev.key == Key.ESC and self.allow_escape:
                return None
            # ignore others

def select_menu(
    title: str,
    options: list[tuple[str, str]],
    footer: str | None = None
) -> str | None:
    items = [MenuItem(label=o[0], value=o[1]) for o in options]
    # Default footer includes B hint unless a custom footer is provided
    if footer is None:
        footer = "↑/↓ or W/S to move • Enter to select • B for Menu • Esc to exit"
    return Menu(title, items, allow_escape=True, footer=footer).run()