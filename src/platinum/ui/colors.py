from __future__ import annotations
import os

def get_color_code(name: str) -> str:
    """Get ANSI color code by name, returns empty string if colors disabled."""
    if os.environ.get('PLAT_COLOR_DISABLED') == '1':
        return ''
    
    codes = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bold': '\033[1m',
        'reset': '\033[0m'
    }
    return codes.get(name, '')

def colored_text(text: str, color: str) -> str:
    """Wrap text in color codes if colors are enabled."""
    if os.environ.get('PLAT_COLOR_DISABLED') == '1':
        return text
    color_code = get_color_code(color)
    reset_code = get_color_code('reset')
    return f"{color_code}{text}{reset_code}"