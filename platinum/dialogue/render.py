from __future__ import annotations
from platinum.ui.typewriter import type_out
from platinum.core.logging import logger

def render_line(speaker_key: str | None, text: str, characters: dict, speed: int):
    if speaker_key:
        speaker = characters.get(speaker_key, speaker_key.upper())
        output = f"{speaker}: {text}"
    else:
        output = text
    logger.debug("RenderDialogue", speaker=speaker_key or "-", chars=len(text))
    type_out(output, speed)