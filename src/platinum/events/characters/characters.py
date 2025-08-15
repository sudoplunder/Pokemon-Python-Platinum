import json
from pathlib import Path
CHAR_PATH = Path("assets/dialogue/en/characters.json")
class CharacterNames:
    def __init__(self):
        self._map = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    def display(self, key: str) -> str:
        return self._map.get(key, key)
characters = CharacterNames()
