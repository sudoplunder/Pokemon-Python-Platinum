from __future__ import annotations
from ..ui.colors import colored_text

def draw_hp_bar(current: int, max_hp: int, width: int = 20) -> str:
    if max_hp <= 0:
        return "█" * width
    
    ratio = current / max_hp
    filled = int(ratio * width)
    empty = width - filled
    
    # Color based on HP percentage
    if ratio > 0.5:
        color = "green"
    elif ratio > 0.2:
        color = "yellow"  
    else:
        color = "red"
    
    bar = "█" * filled + "░" * empty
    return colored_text(bar, color)

def format_battle_text(text: str) -> str:
    """Format battle text with consistent styling."""
    return colored_text(text, "white")