"""
Lightweight logger used across the project.
Color output if colorama is present; degrades gracefully if not.
"""
from __future__ import annotations
import sys
from datetime import datetime
from typing import Literal, Any

Level = Literal["DEBUG","INFO","WARN","ERROR"]

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    COLORS = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED
    }
    RESET = Style.RESET_ALL
except Exception:
    COLORS = {"DEBUG":"", "INFO":"", "WARN":"", "ERROR":""}
    RESET = ""

class Logger:
    _order = {"DEBUG":10,"INFO":20,"WARN":30,"ERROR":40}
    def __init__(self, level: Level = "INFO"):
        self.threshold = self._order[level]

    def set_level(self, level: Level):
        self.threshold = self._order.get(level, 20)

    def _emit(self, lvl: Level, msg: str, **extra: Any):
        if self._order[lvl] < self.threshold:
            return
        ts = datetime.utcnow().isoformat(timespec="seconds")
        extras = ""
        if extra:
            kv = " ".join(f"{k}={v}" for k,v in extra.items())
            extras = " " + kv
        color = COLORS[lvl]
        sys.stdout.write(f"{color}{ts} [{lvl}] {msg}{extras}{RESET}\n")

    def debug(self, msg: str, **kw): self._emit("DEBUG", msg, **kw)
    def info(self, msg: str, **kw): self._emit("INFO", msg, **kw)
    def warn(self, msg: str, **kw): self._emit("WARN", msg, **kw)
    def error(self, msg: str, **kw): self._emit("ERROR", msg, **kw)

logger = Logger("INFO")