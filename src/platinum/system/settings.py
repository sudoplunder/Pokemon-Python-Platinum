from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, List
from platinum.core.logging import logger

SETTINGS_FILENAME = ".platinum_settings.json"

@dataclass
class SettingsData:
    dialogue_mode: str = "base"   # concise, base, expanded, alt
    text_speed: int = 2           # 1 fast, 2 normal, 3 slow
    log_level: str = "INFO"

    def normalize(self):
        if self.dialogue_mode not in {"concise","base","expanded","alt"}:
            self.dialogue_mode = "base"
        if self.text_speed not in {1,2,3}:
            self.text_speed = 2
        if self.log_level not in {"DEBUG","INFO","WARN","ERROR"}:
            self.log_level = "INFO"

class Settings:
    def __init__(self, data: SettingsData, path: Path):
        self.data = data
        self.path = path
        self._listeners: List[Callable[[SettingsData], None]] = []

    @classmethod
    def _resolve_path(cls) -> Path:
        home = Path(os.path.expanduser("~"))
        if home.is_dir() and os.access(home, os.W_OK):
            return home / SETTINGS_FILENAME
        return Path.cwd() / SETTINGS_FILENAME

    @classmethod
    def load(cls) -> "Settings":
        path = cls._resolve_path()
        if path.exists():
            try:
                data = SettingsData(**json.loads(path.read_text()))
                data.normalize()
                logger.debug("Loaded settings", path=str(path))
                return cls(data, path)
            except Exception as e:
                logger.warn("Failed to parse settings, using defaults", error=str(e))
        return cls(SettingsData(), path)

    def save(self):
        try:
            self.path.write_text(json.dumps(asdict(self.data), indent=2))
            logger.debug("Settings saved", path=str(self.path))
        except Exception as e:
            logger.error("Failed to save settings", error=str(e))

    def on_change(self, fn: Callable[[SettingsData], None]):
        self._listeners.append(fn)

    def _notify(self):
        for fn in self._listeners:
            fn(self.data)

    def interactive_menu(self):
        print("\n-- Options --")
        print(f"1) Dialogue Mode (concise/base/expanded/alt) [{self.data.dialogue_mode}]")
        print(f"2) Text Speed (1 fast / 2 normal / 3 slow) [{self.data.text_speed}]")
        print(f"3) Log Level (DEBUG/INFO/WARN/ERROR) [{self.data.log_level}]")
        print("Enter number or blank to return.")
        choice = input("> ").strip()
        if choice == "1":
            mode = input("Mode: ").strip().lower()
            self.data.dialogue_mode = mode
        elif choice == "2":
            sp = input("Speed: ").strip()
            if sp.isdigit():
                self.data.text_speed = int(sp)
        elif choice == "3":
            lvl = input("Level: ").strip().upper()
            self.data.log_level = lvl
        self.data.normalize()
        from platinum.core.logging import logger as global_logger
        global_logger.set_level(self.data.log_level)  # dynamic adjust
        self.save()
        self._notify()