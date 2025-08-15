"""
Scripted Platinum-style opening sequence with multi-sparkle burst.

Timeline:
  0.00s  music + type creators lines
  6.00s  sparkle burst (multi) -> wipe -> type legal lines
 21.50s  wipe -> logo + prompt

Config: assets/config/opening_config.json (see multi_sparkle section)
Env Overrides:
  PLAT_OPENING_TIME_OFFSET  (shift event times)
  PLAT_OPENING_SPEED_SCALE  (typing speed scale)

Skip: any key jumps to final logo (still requires key to proceed).
"""
from __future__ import annotations
import json, os, sys, time, threading, random, re, datetime
from pathlib import Path
from typing import List, Callable

from platinum.ui.logo import colored_logo
from platinum.audio.player import audio
from platinum.ui.keys import read_key, flush_input
from platinum.core.logging import logger

CONFIG_PATH = Path("assets/config/opening_config.json")

CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
RESET = "\033[0m"


def _term_size():
    try:
        import shutil
        cols, rows = shutil.get_terminal_size((80, 24))
        return cols, rows
    except Exception:
        return 80, 24


def _load_config():
    if CONFIG_PATH.is_file():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warn("OpeningConfigParseFailed", error=str(e))
    return {}


class MusicPlayer:
    """Thin adapter kept for backward compatibility; delegates to audio engine."""
    def __init__(self, path: Path):
        self.path = path
        self.started = False

    def play(self):
        if self.path.is_file() and not self.started:
            audio.play_music(self.path, loop=False)
            self.started = True

    def fadeout(self, ms=800):
        audio.fadeout(ms)


class SkipListener:
    def __init__(self):
        self.skip_requested = False
        self._thread = threading.Thread(target=self._listen, daemon=True)

    def start(self):
        self._thread.start()

    def _listen(self):
        try:
            # Capture only the first key to request skip, then flush any burst of presses
            read_key()
            self.skip_requested = True
            flush_input()  # debounce: clear extra buffered keys
        except Exception:
            pass


def _move_cursor(row: int, col: int):
    sys.stdout.write(f"\033[{row+1};{col+1}H")


def _center_block_positions(lines: List[str]) -> tuple[int, List[tuple[int, int]]]:
    cols, rows = _term_size()
    top_offset = max(2, (rows // 2) - len(lines))
    positions = []
    for i, line in enumerate(lines):
        width = len(line)
        start_col = max(0, (cols - width) // 2)
        positions.append((top_offset + i, start_col))
    return top_offset, positions


def _type_lines(lines: List[str], char_interval: float, speed_scale: float,
                cutoff_time: float | None, skip_flag: Callable[[], bool]):
    top_offset, positions = _center_block_positions(lines)
    for (line, (r, c)) in zip(lines, positions):
        rendered = ""
        for ch in line:
            if skip_flag():
                return
            now = time.monotonic()
            if cutoff_time is not None and now >= cutoff_time:
                _move_cursor(r, c)
                sys.stdout.write(line)
                sys.stdout.flush()
                rendered = line
                break
            rendered += ch
            _move_cursor(r, c)
            sys.stdout.write(rendered)
            sys.stdout.flush()
            time.sleep(max(0, char_interval / max(0.0001, speed_scale)))
        _move_cursor(r, c)
        sys.stdout.write(line)
        sys.stdout.flush()


def _wipe():
    sys.stdout.write(CLEAR)
    sys.stdout.flush()


def _auto_update_year_ranges(lines: list[str]) -> list[str]:
    """Update broad franchise ranges to current year while preserving fixed product ranges.

    Rules:
      - Replace {YEAR} / {CURRENT_YEAR} placeholders with current year.
      - For ranges start–end: if end < current_year AND (start <= 1996 or (end - start) > 1), extend to current year.
      - Leave short 1-year or 2-year specific ranges (like 2008–2009) untouched so original product span stays accurate.
    """
    current_year = datetime.datetime.now().year
    updated = []
    range_pattern = re.compile(r"(\b)(\d{4})[–-](\d{4})(\b)")
    for line in lines:
        newline = line.replace("{YEAR}", str(current_year)).replace("{CURRENT_YEAR}", str(current_year))

        def repl(m):
            start = int(m.group(2))
            end = int(m.group(3))
            span = end - start
            if end < current_year and (start <= 1996 or span > 1):
                return f"{m.group(1)}{start}–{current_year}{m.group(4)}"
            return m.group(0)

        newline = range_pattern.sub(repl, newline)
        updated.append(newline)
    return updated


class Sparkle:
    def __init__(self, r: int, c: int, phase_offset: float, color: str | None):
        self.r = r
        self.c = c
        self.phase_offset = phase_offset
        self.last_frame_index = -1
        self.color = color


def _sparkle_burst(frames: List[str],
                   frame_interval: float,
                   duration: float,
                   lines: List[str],
                   skip_flag: Callable[[], bool],
                   cfg: dict):
    if not frames or duration <= 0:
        return
    cols, rows = _term_size()
    top_offset, _ = _center_block_positions(lines)
    widest = max((len(l) for l in lines), default=0)

    count = int(cfg.get("count", 12))
    vertical_offset = int(cfg.get("vertical_offset", -1))
    extra_height_pad = int(cfg.get("extra_height_pad", 1))
    horizontal_pad = int(cfg.get("horizontal_pad_chars", 4))
    burst_seed = cfg.get("seed", None)

    rng = random.Random(burst_seed if isinstance(burst_seed, int) else None)
    if burst_seed is None:
        rng.seed(time.time_ns())

    region_top = max(0, top_offset + vertical_offset)
    region_bottom = min(rows - 2, top_offset + len(lines) - 1 + extra_height_pad)
    region_height = max(1, region_bottom - region_top + 1)
    region_width = widest + 2 * horizontal_pad
    region_left = max(0, (cols - widest) // 2 - horizontal_pad)
    region_right = min(cols - 1, region_left + region_width)
    region_width = region_right - region_left + 1

    colors = cfg.get("color_codes") or ["31", "91"]  # default red shades
    if not isinstance(colors, list):
        colors = ["31", "91"]
    sparkles: List[Sparkle] = []
    for _ in range(count):
        sr = region_top + rng.randrange(region_height)
        sc = region_left + rng.randrange(region_width)
        phase = rng.random() * frame_interval * len(frames)
        color = rng.choice(colors) if colors else None
        sparkles.append(Sparkle(sr, sc, phase, color))

    start = time.monotonic()
    frame_duration = frame_interval * len(frames)
    while True:
        if skip_flag():
            break
        elapsed = time.monotonic() - start
        if elapsed >= duration:
            break
        for sp in sparkles:
            t = (elapsed + sp.phase_offset) % frame_duration
            idx = int(t // frame_interval) % len(frames)
            if idx != sp.last_frame_index:
                frame = frames[idx]
                if sp.color:
                    frame = f"\033[{sp.color}m{frame}\033[0m"
                _move_cursor(sp.r, sp.c)
                sys.stdout.write(frame)
                if sp.last_frame_index != -1:
                    prev_len = len(frames[sp.last_frame_index])
                    if prev_len > len(frame):
                        sys.stdout.write(" " * (prev_len - len(frame)))
                sp.last_frame_index = idx
        sys.stdout.flush()
        time.sleep(0.02)

    blank = " "
    for sp in sparkles:
        _move_cursor(sp.r, sp.c)
        sys.stdout.write(blank)
    sys.stdout.flush()


def _show_logo_block(prompt: str, cfg: dict | None = None):
    """Render the centered logo + tagline; return layout + candidate space positions.

    Returns (start_row, left_col, art_height, art_width, space_positions) where
    space_positions is a list of (row,col) inside the logo art whose character
    is a space (safe for idle sparkle overlay without overwriting inked glyphs).
    """
    _wipe()
    sys.stdout.write(HIDE_CURSOR)
    raw_logo = colored_logo(False).strip('\n')
    raw_lines = raw_logo.splitlines()
    colored_lines = [f"\033[33m{ln}\033[0m" for ln in raw_lines]
    cols, rows = _term_size()
    art_width = max((len(l) for l in raw_lines), default=0)
    art_height = len(raw_lines)
    tagline_lines = ["Pokémon Platinum Python Version", prompt]
    # Tagline colors (optional) from config: logo_tagline_colors list of ANSI codes
    tagline_colors = []
    if cfg:
        tagline_colors = cfg.get("logo_tagline_colors", []) or []
    total_height = art_height + len(tagline_lines)
    start_row = max(0, (rows - total_height) // 2)
    left_col = max(0, (cols - art_width) // 2)

    # Draw logo
    for i, line in enumerate(colored_lines):
        _move_cursor(start_row + i, left_col)
        sys.stdout.write(line + "\n")

    # Draw taglines
    for offset, line in enumerate(tagline_lines):
        width = len(line)
        col = max(0, (cols - width) // 2)
        _move_cursor(start_row + art_height + offset, col)
        if tagline_colors and offset < len(tagline_colors) and tagline_colors[offset]:
            sys.stdout.write(f"\033[{tagline_colors[offset]}m{line}\033[0m\n")
        else:
            sys.stdout.write(line + "\n")
    sys.stdout.flush()

    # Collect candidate positions (spaces) within the logo area only
    space_positions: list[tuple[int,int]] = []
    for i, raw in enumerate(raw_lines):
        row = start_row + i
        for j, ch in enumerate(raw):
            if ch == ' ':
                space_positions.append((row, left_col + j))
    return start_row, left_col, art_height, art_width, space_positions


class _IdleSparkle:
    __slots__ = ("r","c","start","frame_count","_blink_total","_blink_interval")
    def __init__(self, r:int, c:int, start:float, frame_count:int):
        self.r=r; self.c=c; self.start=start; self.frame_count=frame_count
        # Defaults for optional blink metadata (may be overwritten later)
        self._blink_total = 0.0
        self._blink_interval = 0.0


def _idle_logo_sparkles(space_positions: list[tuple[int,int]],
                        frames: list[str],
                        frame_interval: float,
                        count: int,
                        color_codes: list[str],
                        stop_event: threading.Event,
                        eyes_cfg: dict | None = None,
                        ring_positions: list[tuple[int,int]] | None = None):
    if not frames or not space_positions or count <= 0:
        return
    # Build a symmetric twinkle sequence (fade in/out effect) if >2 frames
    if len(frames) > 2:
        seq = frames + frames[-2:0:-1]
    else:
        seq = frames
    rng = random.Random()
    active: list[_IdleSparkle] = []
    # Choose per-sparkle color (kept constant across its life) by storing idx in separate map
    color_for: dict[_IdleSparkle, str] = {}
    # Giratina "eyes" effect (paired animated glyphs) config
    eyes_cfg = eyes_cfg or {}
    eyes_enabled = bool(eyes_cfg.get("enabled", True))
    eyes_interval = float(eyes_cfg.get("interval", 3.5))  # seconds between spawns
    eyes_frames = eyes_cfg.get("frames", ["·","•","●"])  # used to map intensity
    eyes_colors = eyes_cfg.get("color_codes", ["31","91"])  # red variants
    eyes_gap = int(eyes_cfg.get("gap", 3))  # horizontal gap between pair
    eyes_fade_in = float(eyes_cfg.get("fade_in", 1.0))
    eyes_sustain = float(eyes_cfg.get("sustain", 4.0))
    eyes_fade_out = float(eyes_cfg.get("fade_out", 1.0))
    eyes_total = max(0.1, eyes_fade_in + eyes_sustain + eyes_fade_out)
    # Blinking configuration
    blink_enabled = bool(eyes_cfg.get("blink_enabled", True))
    blink_probability = float(eyes_cfg.get("blink_probability", 0.6))
    blink_cycles_min = int(eyes_cfg.get("blink_cycles_min", 1))
    blink_cycles_max = int(eyes_cfg.get("blink_cycles_max", 2))
    blink_cycle_interval = float(eyes_cfg.get("blink_cycle_interval", 0.18))  # seconds ON then seconds OFF (pair -> 2*interval)
    eyes_last_spawn = 0.0
    # Track eyes entries (reuse _IdleSparkle for position but custom timing handling)
    eyes_active: list[_IdleSparkle] = []
    eyes_color_for: dict[_IdleSparkle, str] = {}
    last_spawn = 0.0
    spawn_gap = max(0.15, frame_interval * len(seq) * 0.75)
    # Immediate pre-population so user sees motion instantly (avoid perceived static frame)
    prepopulate = min(count, max(3, count // 2))
    now0 = time.monotonic()
    for _ in range(prepopulate):
        spot = rng.choice(space_positions)
        sp = _IdleSparkle(spot[0], spot[1], now0 - rng.random() * frame_interval * (len(seq)-1), len(seq))
        active.append(sp)
        if color_codes:
            color_for[sp] = rng.choice(color_codes)
    try:
        while not stop_event.is_set():
            now = time.monotonic()
            # Spawn new sparkles if below quota
            if (now - last_spawn) >= spawn_gap and len(active) < count:
                spot = rng.choice(space_positions)
                sp = _IdleSparkle(spot[0], spot[1], now, len(seq))
                active.append(sp)
                if color_codes:
                    color_for[sp] = rng.choice(color_codes)
                last_spawn = now
            # Render
            still: list[_IdleSparkle] = []
            for sp in active:
                idx = int((now - sp.start) / frame_interval)
                if idx >= sp.frame_count:
                    # clear old position
                    _move_cursor(sp.r, sp.c)
                    sys.stdout.write(' ')
                    continue
                frame = seq[idx]
                color = color_for.get(sp)
                if color:
                    frame_out = f"\033[{color}m{frame}\033[0m"
                else:
                    frame_out = frame
                _move_cursor(sp.r, sp.c)
                sys.stdout.write(frame_out)
                still.append(sp)
            active = still

            # Spawn eyes
            # Spawn a new eye pair only if none currently active
            if eyes_enabled and not eyes_active and (now - eyes_last_spawn) >= eyes_interval and ring_positions:
                # pick a base position that leaves room for second eye
                base_candidates = [p for p in ring_positions if (p[0], p[1] + eyes_gap) in ring_positions]
                if base_candidates:
                    base = rng.choice(base_candidates)
                    eyes_obj = _IdleSparkle(base[0], base[1], now, 1)
                    # Pre-set blink attributes to safe defaults before any logic
                    eyes_obj._blink_total = 0.0  # type: ignore[attr-defined]
                    eyes_obj._blink_interval = blink_cycle_interval  # type: ignore[attr-defined]
                    # Decide blink plan (may overwrite defaults)
                    if blink_enabled and rng.random() < blink_probability:
                        cycles = rng.randint(blink_cycles_min, max(blink_cycles_min, blink_cycles_max))
                        eyes_obj._blink_total = max(0.0, cycles * blink_cycle_interval * 2.0)  # type: ignore[attr-defined]
                    eyes_active.append(eyes_obj)
                    eyes_color_for[eyes_obj] = rng.choice(eyes_colors)
                    eyes_last_spawn = now

            # Render eyes
            eyes_still: list[_IdleSparkle] = []
            for eye in eyes_active:
                t = now - eye.start
                blink_total = getattr(eye, "_blink_total", 0.0)
                blink_interval = getattr(eye, "_blink_interval", blink_cycle_interval)
                # Blink phase handling
                if blink_total > 0 and t < blink_total:
                    # Determine if visible this sub-cycle
                    # Each full ON+OFF spans 2*blink_interval; show during first half
                    cycle_pos = t % (2.0 * blink_interval)
                    visible = cycle_pos < blink_interval * 0.55  # slightly shorter ON to feel like a blink
                    if visible:
                        glyph = eyes_frames[-1]  # brightest frame for blink flashes
                        color = eyes_color_for.get(eye, "31")
                        colored = f"\033[{color}m{glyph}\033[0m"
                        _move_cursor(eye.r, eye.c)
                        sys.stdout.write(colored)
                        _move_cursor(eye.r, eye.c + eyes_gap)
                        sys.stdout.write(colored)
                    else:
                        # Clear both positions while closed
                        _move_cursor(eye.r, eye.c)
                        sys.stdout.write(' ')
                        _move_cursor(eye.r, eye.c + eyes_gap)
                        sys.stdout.write(' ')
                    eyes_still.append(eye)
                    continue  # skip fade logic until blink phase done

                # Adjust time to exclude blink phase for fade progression
                adj_t = t - blink_total
                if adj_t >= eyes_total:
                    _move_cursor(eye.r, eye.c)
                    sys.stdout.write(' ')
                    _move_cursor(eye.r, eye.c + eyes_gap)
                    sys.stdout.write(' ')
                    eyes_last_spawn = now  # start cooldown after disappearance
                    continue
                # Determine phase on adjusted timeline
                if adj_t < eyes_fade_in:
                    ratio = adj_t / max(0.001, eyes_fade_in)
                elif adj_t < eyes_fade_in + eyes_sustain:
                    ratio = 1.0
                else:
                    # fade out
                    out_t = adj_t - eyes_fade_in - eyes_sustain
                    ratio = 1.0 - out_t / max(0.001, eyes_fade_out)
                # Map ratio to frame index
                fi = int(ratio * (len(eyes_frames) - 1)) if len(eyes_frames) > 1 else 0
                fi = max(0, min(len(eyes_frames) - 1, fi))
                glyph = eyes_frames[fi]
                color = eyes_color_for.get(eye, "31")
                colored = f"\033[{color}m{glyph}\033[0m"
                _move_cursor(eye.r, eye.c)
                sys.stdout.write(colored)
                _move_cursor(eye.r, eye.c + eyes_gap)
                sys.stdout.write(colored)
                eyes_still.append(eye)
            eyes_active = eyes_still
            sys.stdout.flush()
            time.sleep(0.05)
    finally:
        # Clean up any remaining sparkle artifacts
        for sp in active:
            _move_cursor(sp.r, sp.c)
            sys.stdout.write(' ')
        for eye in eyes_active:
            _move_cursor(eye.r, eye.c)
            sys.stdout.write(' ')
            _move_cursor(eye.r, eye.c + eyes_gap)
            sys.stdout.write(' ')
        sys.stdout.flush()


def show_opening(wait_for_key: bool = True):
    cfg = _load_config()
    creators_lines = cfg.get("creators_lines", ["Created by ..."])
    legal_lines = _auto_update_year_ranges(cfg.get("legal_lines", ["Legal text"]))
    timings = cfg.get("timings", {})
    twinkle_at = float(timings.get("twinkle_at", 6.0))
    logo_at = float(timings.get("logo_at", 21.5))
    char_int_creators = float(cfg.get("char_interval_creators", 0.035))
    char_int_legal = float(cfg.get("char_interval_legal", 0.03))
    frames = cfg.get("twinkle_frames", [])
    default_frame_interval = float(cfg.get("twinkle_frame_interval", 0.08))
    multi_cfg = cfg.get("multi_sparkle", {})
    multi_enabled = bool(multi_cfg.get("enabled", False))
    burst_frame_interval = float(multi_cfg.get("frame_interval", default_frame_interval))
    post_logo_prompt = cfg.get("post_logo_prompt", "Press Enter To Start")
    giratina_cry = cfg.get("giratina_cry", "assets/audio/sfx/cries/487_giratina.ogg")
    music_path = Path(cfg.get("music", ""))

    time_offset = float(os.getenv("PLAT_OPENING_TIME_OFFSET", "0") or 0)
    speed_scale = float(os.getenv("PLAT_OPENING_SPEED_SCALE", "1") or 1)

    twinkle_at += time_offset
    logo_at += time_offset

    skip_listener = SkipListener()
    skip_listener.start()

    music = MusicPlayer(music_path)
    music.play()

    sys.stdout.write(CLEAR + HIDE_CURSOR)
    sys.stdout.flush()

    start_time = time.monotonic()
    cutoff_creators = start_time + twinkle_at

    _type_lines(
        creators_lines,
        char_interval=char_int_creators,
        speed_scale=speed_scale,
        cutoff_time=cutoff_creators,
        skip_flag=lambda: skip_listener.skip_requested
    )

    while not skip_listener.skip_requested and time.monotonic() < cutoff_creators:
        time.sleep(0.01)

    if not skip_listener.skip_requested:
        if multi_enabled:
            _sparkle_burst(
                frames=frames,
                frame_interval=burst_frame_interval,
                duration=float(multi_cfg.get("duration", 0.8)),
                lines=creators_lines,
                skip_flag=lambda: skip_listener.skip_requested,
                cfg=multi_cfg
            )
        else:
            _sparkle_burst(
                frames=frames,
                frame_interval=default_frame_interval,
                duration=0.25,
                lines=creators_lines,
                skip_flag=lambda: skip_listener.skip_requested,
                cfg={"count": 1, "vertical_offset": -1, "extra_height_pad": 0, "horizontal_pad_chars": 0}
            )
        if not skip_listener.skip_requested:
            _wipe()

    cutoff_legal = start_time + logo_at
    if not skip_listener.skip_requested:
        _type_lines(
            legal_lines,
            char_interval=char_int_legal,
            speed_scale=speed_scale,
            cutoff_time=cutoff_legal,
            skip_flag=lambda: skip_listener.skip_requested
        )
        while not skip_listener.skip_requested and time.monotonic() < cutoff_legal:
            time.sleep(0.01)

    layout = _show_logo_block(post_logo_prompt, cfg)
    start_row, left_col, art_height, art_width, inner_space_positions = layout

    # Build candidate positions OUTSIDE the logo art (ring/bands) to avoid overwriting glyphs
    cols, rows = _term_size()
    tagline_rows = {start_row + art_height, start_row + art_height + 1}
    ring_positions: list[tuple[int,int]] = []
    def add_band(r_start, r_end, c_start, c_end):
        for r in range(r_start, r_end+1):
            if r < 0 or r >= rows or r in tagline_rows:
                continue
            for c in range(c_start, c_end+1):
                if c < 0 or c >= cols:
                    continue
                ring_positions.append((r,c))
    # Top band
    add_band(start_row-2, start_row-1, left_col-4, left_col+art_width+3)
    # Left band
    add_band(start_row, start_row+art_height-1, left_col-6, left_col-2)
    # Right band
    add_band(start_row, start_row+art_height-1, left_col+art_width+1, left_col+art_width+5)
    # (Optional bottom band excluded to keep prompt clean)
    if not ring_positions:
        ring_positions = inner_space_positions  # fallback

    # Idle sparkle background while waiting at logo
    logo_idle_cfg = cfg.get("logo_idle_sparkles", {})
    idle_enabled = bool(logo_idle_cfg.get("enabled", True))
    # Base star count; boost by 10% to increase frequency per request
    base_idle_count = int(logo_idle_cfg.get("count", 10))
    idle_count = max(1, int(round(base_idle_count * 1.10)))
    idle_frame_interval = float(logo_idle_cfg.get("frame_interval", 0.12))
    idle_frames = logo_idle_cfg.get("frames", frames)  # reuse earlier frames by default
    # Default palette: white, grey, red, bright red (no yellow per spec)
    # Duplicate reds implicitly for higher spawn likelihood if user doesn't supply custom list.
    idle_colors = logo_idle_cfg.get("color_codes", ["37","90","31","31","91","91"])  # 31=red, 91=bright red
    # Start idle ambient effects even if an earlier key was pressed to skip to the logo.
    if idle_enabled:
        stop_idle = threading.Event()
        eyes_cfg = cfg.get("logo_idle_eyes", {})
        idle_thread = threading.Thread(
            target=_idle_logo_sparkles,
            args=(ring_positions, idle_frames, idle_frame_interval, idle_count, idle_colors, stop_idle, eyes_cfg, ring_positions),
            daemon=True,
        )
        idle_thread.start()
    else:
        stop_idle = None

    # Keep music playing while the logo + prompt are visible; only fade once user proceeds.
    if wait_for_key:
        # Flush any buffered keys from rapid skip presses before waiting
        flush_input()
        read_key()  # single decisive Enter to proceed
        if 'stop_idle' in locals() and stop_idle:
            stop_idle.set()
            time.sleep(0.12)
        # Stop music then play cry (70% volume)
        music.fadeout(400)
        audio.play_sfx(giratina_cry, volume=0.7)
    else:
        # Non-interactive or fully auto mode: fade music & play cry then continue
        music.fadeout(400)
        audio.play_sfx(giratina_cry, volume=0.7)

    sys.stdout.write(SHOW_CURSOR + RESET)
    sys.stdout.flush()
    logger.info("OpeningComplete")


def show_opening_sequence():
    show_opening(wait_for_key=True)