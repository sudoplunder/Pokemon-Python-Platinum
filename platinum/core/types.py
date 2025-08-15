"""Global type metadata: colors & abbreviations.

Provides:
  TYPE_COLORS_HEX: mapping type -> hex color string (#RRGGBB)
  TYPE_ABBREVIATIONS: mapping type -> 3-letter abbreviation (upper)
  ABBREVIATION_TYPES: reverse mapping
  helper functions for colorized terminal output with graceful fallback.
"""
from __future__ import annotations
from typing import Dict, Tuple
import os, re

TYPE_COLORS_HEX: Dict[str, str] = {
    "normal": "#A8A77A",
    "fire": "#EE8130",
    "water": "#6390F0",
    "electric": "#F7D02C",
    "grass": "#7AC74C",
    "ice": "#96D9D6",
    "fighting": "#C22E28",
    "poison": "#A33EA1",
    "ground": "#E2BF65",
    "flying": "#A98FF3",
    "psychic": "#F95587",
    "bug": "#A6B91A",
    "rock": "#B6A136",
    "ghost": "#735797",
    "dragon": "#6F35FC",
    "dark": "#705746",
    "steel": "#B7B7CE",
}

TYPE_ABBREVIATIONS: Dict[str, str] = {
    "normal": "NRM",
    "fire": "FIR",
    "water": "WTR",
    "grass": "GRS",
    "electric": "ELE",
    "ice": "ICE",
    "fighting": "FGT",
    "poison": "PSN",
    "ground": "GRN",  # Provided as GRN per spec
    "flying": "FLY",
    "psychic": "PSY",
    "bug": "BUG",
    "rock": "RCK",
    "ghost": "GHO",
    "dragon": "DRA",
    "dark": "DRK",
    "steel": "STL",
}

ABBREVIATION_TYPES: Dict[str, str] = {abbr: t for t, abbr in TYPE_ABBREVIATIONS.items()}

_TRUECOLOR = bool(os.environ.get("COLORTERM","" ).lower().find("truecolor") != -1)

try:
    from colorama import Fore, Style
except Exception:  # pragma: no cover
    class _F: RESET = RED = GREEN = YELLOW = MAGENTA = CYAN = BLUE = WHITE = ''
    class _S: RESET_ALL = ''
    Fore=_F(); Style=_S()

_FALLBACK_FORE: Dict[str,str] = {
    "normal": Fore.WHITE,
    "fire": Fore.RED,
    "water": Fore.CYAN,
    "electric": Fore.YELLOW,
    "grass": Fore.GREEN,
    "ice": Fore.CYAN,
    "fighting": Fore.MAGENTA,
    "poison": Fore.MAGENTA,
    "ground": Fore.YELLOW,
    "flying": Fore.WHITE,
    "psychic": Fore.MAGENTA,
    "bug": Fore.GREEN,
    "rock": Fore.YELLOW,
    "ghost": Fore.MAGENTA,
    "dragon": Fore.CYAN,
    "dark": Fore.WHITE,
    "steel": Fore.WHITE,
}

RESET = getattr(Style, 'RESET_ALL', '\x1b[0m')

def _hex_to_rgb(h: str) -> Tuple[int,int,int]:
    h = h.lstrip('#')
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def color_code(type_name: str) -> str:
    t = type_name.lower()
    hex_val = TYPE_COLORS_HEX.get(t)
    if not hex_val:
        return ''
    if _TRUECOLOR:
        r,g,b = _hex_to_rgb(hex_val)
        return f"\033[38;2;{r};{g};{b}m"
    return _FALLBACK_FORE.get(t,'')

def colorize_type_text(type_name: str, text: str) -> str:
    code = color_code(type_name)
    if not code:
        return text
    return f"{code}{text}{RESET}"

def type_abbreviation(type_name: str) -> str:
    return TYPE_ABBREVIATIONS.get(type_name.lower(), type_name[:3].upper())

def format_types(types: Tuple[str,...]) -> str:
    parts = [colorize_type_text(t, type_abbreviation(t)) for t in types]
    return '/'.join(parts)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(s: str) -> str:
    return ANSI_ESCAPE_RE.sub('', s)

__all__ = [
    'TYPE_COLORS_HEX','TYPE_ABBREVIATIONS','ABBREVIATION_TYPES',
    'colorize_type_text','type_abbreviation','format_types','strip_ansi'
]
