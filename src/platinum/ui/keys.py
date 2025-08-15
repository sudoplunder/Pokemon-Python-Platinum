"""
Key input abstraction for cross-platform arrow / WASD / Enter navigation.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import sys

class Key(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    ENTER = auto()
    ESC = auto()
    OTHER = auto()

@dataclass
class KeyEvent:
    key: Key
    raw: str | bytes | None = None

def _win_read() -> KeyEvent:
    import msvcrt
    ch = msvcrt.getch()
    if ch in (b"\r", b"\n"):
        return KeyEvent(Key.ENTER, ch)
    if ch == b"\x1b":
        return KeyEvent(Key.ESC, ch)
    if ch in (b"w", b"W"):
        return KeyEvent(Key.UP, ch)
    if ch in (b"s", b"S"):
        return KeyEvent(Key.DOWN, ch)
    if ch in (b"a", b"A"):
        return KeyEvent(Key.LEFT, ch)
    if ch in (b"d", b"D"):
        return KeyEvent(Key.RIGHT, ch)
    # Arrow keys: first byte is 0xe0 or 0x00 then second is code
    if ch in (b"\x00", b"\xe0"):
        nxt = msvcrt.getch()
        mapping = {
            b"H": Key.UP,
            b"P": Key.DOWN,
            b"K": Key.LEFT,
            b"M": Key.RIGHT
        }
        return KeyEvent(mapping.get(nxt, Key.OTHER), ch + nxt)
    return KeyEvent(Key.OTHER, ch)

def _unix_read() -> KeyEvent:
    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\r" or ch == "\n":
            return KeyEvent(Key.ENTER, ch)
        if ch == "\x1b":  # possible escape sequence
            seq = sys.stdin.read(1)
            if seq == "[":
                seq2 = sys.stdin.read(1)
                mapping = {
                    "A": Key.UP,
                    "B": Key.DOWN,
                    "C": Key.RIGHT,
                    "D": Key.LEFT
                }
                return KeyEvent(mapping.get(seq2, Key.OTHER), "\x1b[" + seq2)
            return KeyEvent(Key.ESC, ch)
        if ch in ("w","W"):
            return KeyEvent(Key.UP, ch)
        if ch in ("s","S"):
            return KeyEvent(Key.DOWN, ch)
        if ch in ("a","A"):
            return KeyEvent(Key.LEFT, ch)
        if ch in ("d","D"):
            return KeyEvent(Key.RIGHT, ch)
        return KeyEvent(Key.OTHER, ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def read_key() -> KeyEvent:
    if sys.platform.startswith("win"):
        return _win_read()
    try:
        return _unix_read()
    except Exception:
        # Fallback: read line
        line = sys.stdin.readline().rstrip("\n")
        return KeyEvent({
            "": Key.ENTER,
            "w": Key.UP, "W": Key.UP,
            "s": Key.DOWN, "S": Key.DOWN,
            "a": Key.LEFT, "A": Key.LEFT,
            "d": Key.RIGHT, "D": Key.RIGHT,
            "q": Key.ESC, "Q": Key.ESC
        }.get(line, Key.OTHER), line)