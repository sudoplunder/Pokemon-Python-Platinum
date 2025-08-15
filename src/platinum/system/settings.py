import json
import time
from pathlib import Path
from typing import Dict, Any


class Settings:
    def __init__(self, settings_file: str = None):
        if settings_file is None:
            # Try user home first, fallback to current directory
            home_path = Path.home() / ".platinum_settings.json"
            if home_path.parent.exists():
                settings_file = str(home_path)
            else:
                settings_file = "platinum_settings.json"
        
        self.settings_file = Path(settings_file)
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        if self.settings_file.exists():
            try:
                return json.loads(self.settings_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        
        # Default settings
        return {
            "dialogue_mode": "expanded",
            "text_speed": 1.0
        }
    
    def save(self):
        try:
            self.settings_file.write_text(
                json.dumps(self.settings, indent=2), 
                encoding="utf-8"
            )
        except OSError:
            pass  # Silently fail if we can't save
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        self.settings[key] = value
        self.save()