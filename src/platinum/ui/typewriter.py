import time
import sys


class Typewriter:
    def __init__(self, speed: float = 1.0):
        self.speed = speed
    
    def print(self, text: str, delay_per_char: float = None):
        """Print text with typewriter effect"""
        if delay_per_char is None:
            delay_per_char = 0.03 / self.speed
        
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(delay_per_char)
        print()  # Final newline
    
    def set_speed(self, speed: float):
        """Set typing speed (higher = faster)"""
        self.speed = speed