from __future__ import annotations
import json
from pathlib import Path
from random import Random
from typing import Dict

from platinum.core.logging import logger
from platinum.core.paths import DIALOGUE_EN
from .variant import DialogueEntry
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
                # Single-format system: only 'expanded' retained.
                expanded = value.get("expanded") or value.get("base") or value.get("concise")
                if not expanded:
                    continue
                speaker = value.get("speaker")
                self.entries[key] = DialogueEntry(key, speaker, expanded)
        from platinum.system.settings import Settings
        if getattr(Settings.load().data, 'debug', False):
            logger.debug("DialogueLoaded", entries=len(self.entries), chars=len(self.characters))

    def show(self, key: str):
        """Render a dialogue line by key.

        In the simplified single-format system all lines use the 'expanded'
        text (falling back to base/concise only if legacy files still have
        not yet been cleaned). Missing keys are logged and visibly marked.
        """
        entry = self.entries.get(key)
        if not entry:
            logger.warn("DialogueKeyMissing", key=key)
            print(f"[Missing dialogue: {key}]")
            return
        # Render the single-format (expanded) line
        text = entry.text
        # Basic placeholder substitution if GameContext injected later
        ctx = getattr(self.settings, "_game_context", None)
        if ctx is None:
            # Alternate path: try global variable injection by monkeypatch in GameContext
            ctx = getattr(self, "_game_context", None)
        if ctx is not None:
            try:
                # Prefer persisted assistant field; fallback to gender rule
                assistant = getattr(ctx.state, 'assistant', None)
                if not assistant:
                    gender = getattr(ctx.state, 'player_gender', 'unspecified')
                    assistant = 'lucas' if gender == 'female' else 'dawn'
                assistant_display = assistant.title()
                from datetime import datetime
                # Use GameState-captured system_time if present else live now
                now_str = getattr(ctx.state, 'system_time', '') or datetime.now().strftime('%H:%M')
                text = (text
                        .replace("{PLAYER}", ctx.state.player_name)
                        .replace("{RIVAL}", ctx.state.rival_name)
                        .replace("{ASSISTANT}", assistant_display)
                        .replace("{SYSTEM_TIME}", now_str))
                # Dynamic rival speaker handling: avoid double prefix like 'RIVAL: Barry:'
                if entry.speaker in ('rival', 'assistant'):
                    if entry.speaker == 'rival':
                        dynamic_name = ctx.state.rival_name
                    else:
                        dynamic_name = assistant_display
                    if text.startswith(f"{dynamic_name}:"):
                        render_speaker = None
                    else:
                        text = f"{dynamic_name}: {text}"
                        render_speaker = None
                else:
                    render_speaker = entry.speaker
            except Exception:
                render_speaker = entry.speaker
        else:
            render_speaker = entry.speaker
        render_line(render_speaker, text, self.characters, self.settings.data.text_speed)