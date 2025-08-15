from __future__ import annotations
import json
from pathlib import Path
from random import Random
from typing import Optional

from platinum.ui.typewriter import type_out

class DialogueManager:
    def __init__(self, settings):
        self.settings = settings
        self.characters = {}
        self.dialogue = {}
        self.random = Random()
        self._load_all()

    def _load_all(self):
        root = Path("assets/dialogue/en")
        chars = root / "characters.json"
        if chars.exists():
            self.characters = json.loads(chars.read_text())
        # Load all core/*.json
        core_dir = root / "core"
        for f in sorted(core_dir.glob("*.json")):
            data = json.loads(f.read_text())
            for k, v in data.items():
                if k.startswith("_"):
                    continue
                self.dialogue[k] = v

    def render(self, key: str):
        entry = self.dialogue.get(key)
        if not entry:
            print(f"[dialogue] Missing key: {key}")
            return
        mode = self.settings.data.dialogue_mode
        text = None
        if mode == "alt":
            # alt: choose any variant except maybe base? gather all variant strings
            candidates = [entry.get(x) for x in ("expanded","base","concise") if entry.get(x)]
            if candidates:
                text = self.random.choice(candidates)
        else:
            text = entry.get(mode) or entry.get("base")
        if not text:
            text = "<MISSING TEXT>"
        speaker = entry.get("speaker")
        if speaker:
            speaker_resolved = self.characters.get(speaker, speaker.upper())
            out = f"{speaker_resolved}: {text}"
        else:
            out = text
        type_out(out, self.settings.data.text_speed)