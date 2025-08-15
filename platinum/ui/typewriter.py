"""
Typewriter effect utility for text display.
"""
import sys
import time


def typewriter_effect(text: str, delay: float = 0.03, newline: bool = True):
    """
    Display text with a typewriter effect.
    
    Args:
        text: The text to display
        delay: Delay between characters (seconds)
        newline: Whether to add a newline at the end
    """
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    
    if newline:
        print()


def typewriter_lines(lines: list, line_delay: float = 0.5, char_delay: float = 0.03):
    """
    Display multiple lines with typewriter effect and pauses between lines.
    
    Args:
        lines: List of strings to display
        line_delay: Delay between lines (seconds)
        char_delay: Delay between characters (seconds)
    """
    for i, line in enumerate(lines):
        if i > 0:
            time.sleep(line_delay)
        typewriter_effect(line, delay=char_delay, newline=True)