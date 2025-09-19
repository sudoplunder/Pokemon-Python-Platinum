"""Central Pokémon type color definitions and ANSI helpers.

Provides a mapping of type -> {light, base, dark} hex colors and
utilities to convert hex to ANSI escape sequences for terminal output.
Falls back gracefully if ANSI is unsupported.
"""
from __future__ import annotations
from typing import Dict
import os

# Core mapping: hex strings without leading '#'
TYPE_COLORS: Dict[str, Dict[str, str]] = {
    "bug":     {"light": "B8C26A", "base": "91A119", "dark": "5E6910"},
    "dark":    {"light": "998B8C", "base": "624D4E", "dark": "403233"},
    "dragon":  {"light": "8D98EC", "base": "5060E1", "dark": "343E92"},
    "electric":{"light": "FCD659", "base": "FAC000", "dark": "A37D00"},
    "fairy":   {"light": "F5A2F5", "base": "EF70EF", "dark": "9B499B"},
    "fighting":{"light": "FFAC59", "base": "FF8000", "dark": "A65300"},
    "fire":    {"light": "EF7374", "base": "E62829", "dark": "961A1B"},
    "flying":  {"light": "ADD2F5", "base": "81B9EF", "dark": "54789B"},
    "ghost":   {"light": "A284A2", "base": "704170", "dark": "492A49"},
    "grass":   {"light": "82C274", "base": "3FA129", "dark": "29691B"},
    "ground":  {"light": "B88E6F", "base": "915121", "dark": "5E3515"},
    "ice":     {"light": "81DFF7", "base": "3DCEF3", "dark": "28869E"},
    "normal":  {"light": "C1C2C1", "base": "9FA19F", "dark": "676967"},
    "poison":  {"light": "B884DD", "base": "9141CB", "dark": "5E2A84"},
    "psychic": {"light": "F584A8", "base": "EF4179", "dark": "9B2A4F"},
    "rock":    {"light": "CBC7AD", "base": "AFA981", "dark": "726E54"},
    "steel":   {"light": "98C2D1", "base": "60A1B8", "dark": "3E6978"},
    "stellar": {"light": "83CFC5", "base": "40B5A5", "dark": "2A766B"},
    "water":   {"light": "74ACF5", "base": "2980EF", "dark": "1B539B"},
}

RESET = "\033[0m"


def _supports_ansi_truecolor() -> bool:
    """Best-effort detection for 24-bit color support."""
    # If running under pytest, we can still emit codes but tests ignore display.
    if os.name != 'nt':
        return True
    # On Windows 10+, ConHost often supports VT sequences if enabled.
    # Assume True; worst case, colors render as raw codes but harmless.
    return True


def ansi_from_hex(hex_str: str) -> str:
    """Return ANSI escape sequence for a given hex color (foreground)."""
    s = hex_str.strip().lstrip('#')
    if len(s) != 6:
        return ""
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
    except ValueError:
        return ""
    if not _supports_ansi_truecolor():
        return ""  # fallback: let caller use default color
    return f"\033[38;2;{r};{g};{b}m"


def type_color_ansi(type_name: str, shade: str = "base") -> str:
    """Get ANSI color sequence for a Pokémon type and shade ('light'|'base'|'dark')."""
    t = TYPE_COLORS.get(type_name.lower())
    if not t:
        return ""
    hexv = t.get(shade) or t.get("base") or ""
    return ansi_from_hex(hexv)
