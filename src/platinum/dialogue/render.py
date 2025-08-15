from __future__ import annotations
from platinum.ui.typewriter import type_out
from platinum.core.logging import logger

def render_line(speaker_key: str | None, text: str, characters: dict, speed: int):
    if speaker_key:
        speaker = characters.get(speaker_key, speaker_key.upper())
        out = f"{speaker}: {text}"
    else:
        out = text
    logger.debug("Render dialogue", speaker=speaker_key or "-", length=len(text))
    type_out(out, speed)