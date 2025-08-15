from __future__ import annotations
import json
from pathlib import Path
from platinum.core.logging import logger

SAVE_DIR = Path("saves")
SAVE_FILE = SAVE_DIR / "save1.json"

class SaveStore:
    def write(self, data: dict):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        SAVE_FILE.write_text(json.dumps(data, indent=2))
        logger.info("GameSaved", path=str(SAVE_FILE))
    
    def read(self) -> dict | None:
        if not SAVE_FILE.is_file():
            return None
        try:
            return json.loads(SAVE_FILE.read_text())
        except Exception as e:
            logger.warn("SaveLoadFailed", error=str(e))
            return None
    
    def exists(self) -> bool:
        return SAVE_FILE.is_file()