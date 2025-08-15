from __future__ import annotations
import json
from pathlib import Path
from random import Random
from typing import Dict
from platinum.core.logging import logger
from platinum.dialogue.variant import DialogueEntry, VariantSelector
from platinum.dialogue.render import render_line
from platinum.core.paths import DIALOGUE_EN

class DialogueManager:
    def __init__(self, settings):
        self.settings = settings
        self.characters: Dict[str,str] = {}
        self.entries: Dict[str, DialogueEntry] = {}
        self.rng = Random()
        self.reload()

    def reload(self):
        self.characters.clear()
        self.entries.clear()
        chars = DIALOGUE_EN / "characters.json"
        if chars.exists():
            self.characters = json.loads(chars.read_text())
        core_dir = DIALOGUE_EN / "core"
        if core_dir.is_dir():
            for f in sorted(core_dir.glob("*.json")):
                data = json.loads(f.read_text())
                for k,v in data.items():
                    if k.startswith("_"):
                        continue
                    speaker = v.get("speaker")
                    variants = {vv: v[vv] for vv in ("base","concise","expanded") if vv in v}
                    self.entries[k] = DialogueEntry(k, speaker, variants)
        logger.debug("Dialogue loaded", count=len(self.entries))

    def show(self, key: str):
        entry = self.entries.get(key)
        if not entry:
            logger.warn("Missing dialogue key", key=key)
            print(f"[Missing dialogue: {key}]")
            return
        selector = VariantSelector(self.settings.data.dialogue_mode, self.rng)
        text = selector.select(entry)
        render_line(entry.speaker, text, self.characters, self.settings.data.text_speed)