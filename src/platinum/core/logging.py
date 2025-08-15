from __future__ import annotations
import sys
from datetime import datetime
from typing import Literal, Any

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    COLORS = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERROR": Fore.RED,
    }
except Exception:
    class _Dummy:  # fallback no color
        RESET_ALL = ""
    class _F:
        BLUE = GREEN = YELLOW = RED = ""
    Style = _Dummy()
    COLORS = {"DEBUG":"", "INFO":"", "WARN":"", "ERROR":""}
    Fore = _F()

Level = Literal["DEBUG","INFO","WARN","ERROR"]

class Logger:
    def __init__(self, level: Level = "INFO"):
        self.level_order = {"DEBUG":10,"INFO":20,"WARN":30,"ERROR":40}
        self.threshold = self.level_order[level]

    def set_level(self, level: Level):
        self.threshold = self.level_order[level]

    def _emit(self, level: Level, msg: str, **extra: Any):
        if self.level_order[level] < self.threshold:
            return
        stamp = datetime.utcnow().isoformat(timespec="seconds")
        extrastr = (" " + " ".join(f"{k}={v}" for k,v in extra.items())) if extra else ""
        color = COLORS[level]
        reset = getattr(Style, "RESET_ALL", "")
        sys.stdout.write(f"{color}{stamp} [{level}] {msg}{extrastr}{reset}\n")

    def debug(self, msg: str, **kw): self._emit("DEBUG", msg, **kw)
    def info(self, msg: str, **kw): self._emit("INFO", msg, **kw)
    def warn(self, msg: str, **kw): self._emit("WARN", msg, **kw)
    def error(self, msg: str, **kw): self._emit("ERROR", msg, **kw)

logger = Logger("INFO")