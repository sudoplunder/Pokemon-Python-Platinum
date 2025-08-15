from __future__ import annotations
import platinum.ui.typewriter as tw
import shutil
from textwrap import wrap
from platinum.core.logging import logger
from platinum.system.settings import Settings

def render_line(speaker_key: str | None, text: str, characters: dict, speed: int):
    """Render a single dialogue line with a clean paged UI.

    Behavior:
    - Clears screen before each line (except when debug fast-print is on)
    - Typewriter output
    - Prompts user to press Enter to continue (skipped in automated test env)
    """
    debug = getattr(Settings.load().data, 'debug', False)
    if not debug:
        tw.clear_screen()
    if speaker_key:
        speaker = characters.get(speaker_key, speaker_key.upper())
        output = f"{speaker}: {text}"
        if debug and speaker_key == 'prof':
            output = f"[ROWAN]{output}"
    else:
        output = text
    if debug:
        logger.debug("RenderDialogue", speaker=speaker_key or "-", chars=len(text))
    # Determine terminal width for wrapping
    try:
        width = shutil.get_terminal_size((80, 20)).columns
    except Exception:
        width = 80
    width = max(30, min(width, 100))  # sane bounds
    # Wrap text, but attempt to widen up to 140 columns so each entry fits into <=2 lines
    base_width = width
    candidate_width = base_width
    lines = []
    def do_wrap(w):
        tmp = []
        for paragraph in output.split('\n'):
            if not paragraph.strip():
                tmp.append('')
                continue
            tmp.extend(wrap(paragraph, width=w))
        return tmp or ['']
    lines = do_wrap(candidate_width)
    while len(lines) > 2 and candidate_width < 140:
        candidate_width += 5
        lines = do_wrap(candidate_width)
    # If still more than 2 lines, we will paginate (rare long text)
    if len(lines) <= 2:
        for ln in lines:
            tw.type_out(ln, speed)
        tw.wait_for_continue(debug=debug)
    else:
        LPP = 2
        idx = 0
        total = len(lines)
        while idx < total:
            if idx > 0 and not debug:
                tw.clear_screen()
            page = lines[idx: idx+LPP]
            for ln in page:
                tw.type_out(ln, speed)
            idx += LPP
            tw.wait_for_continue(debug=debug)