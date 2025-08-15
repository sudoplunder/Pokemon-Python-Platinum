"""
Settings management for Pokémon Platinum.

Handles loading, saving, and managing user preferences and game settings.
"""
import json
from pathlib import Path
from typing import Dict, Any


class Settings:
    """Game settings manager."""
    
    def __init__(self, settings_file: str = "platinum_settings.json"):
        self.settings_file = Path(settings_file)
        
        # Default settings
        self.text_speed = "normal"
        self.sound_enabled = True
        self.dialogue_mode = "expanded"
        self.save_slot = 1
        self.debug_mode = False
        
        # Load existing settings if available
        self.load()
    
    def load(self):
        """Load settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Update settings with loaded values
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                        
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings: {e}")
                print("Using default settings.")
    
    def save(self):
        """Save current settings to file."""
        try:
            data = {
                "text_speed": self.text_speed,
                "sound_enabled": self.sound_enabled,
                "dialogue_mode": self.dialogue_mode,
                "save_slot": self.save_slot,
                "debug_mode": self.debug_mode
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except IOError as e:
            print(f"Warning: Could not save settings: {e}")
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self.text_speed = "normal"
        self.sound_enabled = True
        self.dialogue_mode = "expanded"
        self.save_slot = 1
        self.debug_mode = False
    
    def get_text_delay(self) -> float:
        """Get character delay based on text speed setting."""
        speed_map = {
            "fast": 0.01,
            "normal": 0.03,
            "slow": 0.08
        }
        return speed_map.get(self.text_speed, 0.03)
    
    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of current settings."""
        return {
            "text_speed": self.text_speed,
            "sound_enabled": self.sound_enabled,
            "dialogue_mode": self.dialogue_mode,
            "save_slot": self.save_slot,
            "debug_mode": self.debug_mode
        }