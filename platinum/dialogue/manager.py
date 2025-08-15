from __future__ import annotations
import json
from pathlib import Path
from random import Random
from typing import Dict

from platinum.core.logging import logger
from platinum.core.paths import DIALOGUE_EN
from .variant import DialogueEntry, VariantSelector
from .render import render_line

class DialogueManager:
    """
    Loads dialogue JSON assets and renders lines according to the current
    settings (mode + text speed). Keeps data in memory for fast access.
    """
    def __init__(self, settings):
        self.settings = settings
        self.characters: Dict[str, str] = {}
        self.entries: Dict[str, DialogueEntry] = {}
        self.rng = Random()
        self.reload()

    def reload(self):
        self.characters.clear()
        self.entries.clear()
        chars_file = DIALOGUE_EN / "characters.json"
        if chars_file.exists():
            try:
                self.characters = json.loads(chars_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warn("Characters load failed", file=str(chars_file), error=str(e))
        core_dir = DIALOGUE_EN / "core"
        if not core_dir.is_dir():
            logger.warn("Dialogue core directory missing", path=str(core_dir))
            return
        for f in sorted(core_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warn("Dialogue file parse failed", file=str(f), error=str(e))
                continue
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                # collect variants
                variants = {}
                for variant_name in ("base","concise","expanded"):
                    if variant_name in value:
                        variants[variant_name] = value[variant_name]
                if not variants:
                    continue
                speaker = value.get("speaker")
                self.entries[key] = DialogueEntry(key, speaker, variants)
        logger.debug("DialogueLoaded", entries=len(self.entries), chars=len(self.characters))

    def show(self, key: str):
        entry = self.entries.get(key)
        if not entry:
            logger.warn("DialogueKeyMissing", key=key)
            print(f"[Missing dialogue: {key}]")
            return
        selector = VariantSelector(self.settings.data.dialogue_mode, self.rng)
        text = selector.select(entry)
        render_line(entry.speaker, text, self.characters, self.settings.data.text_speed)