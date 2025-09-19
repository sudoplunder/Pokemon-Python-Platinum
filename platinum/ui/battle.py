"""Terminal battle UI (basic) with vertical menus.

Supports simple 1v1 battles for wild or trainer encounters. The loop presents
the main action menu:

  Fight / Pokemon / Bag / Run

Currently Bag is a placeholder; Pokemon allows switching if other healthy
party members exist. Run is blocked for trainer battles. Enemy AI picks a
random usable move.

Intentionally minimal (no animations, status messages aggregated). Designed so
tests can bypass by not setting the interactive flag in event actions.
"""
from __future__ import annotations
from typing import Optional, List, Dict
import random
from platinum.ui.menu_nav import Menu, MenuItem
import re
from platinum.battle.session import BattleSession, Party
from platinum.battle.core import Move, Battler
from platinum.core.types import format_types, type_abbreviation, colorize_type_text, TYPE_COLORS_HEX
from platinum.ui import typewriter as tw
from platinum.battle.experience import required_exp_for_level, growth_rate
from platinum.audio.player import audio
import time
import sys
import os
import math

# Rich imports for beautiful terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.align import Align
from rich.columns import Columns
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich import print as rprint

# Use the same console as the menu system for consistent rendering
from platinum.ui.menu_nav import menu_console as console

try:
    from colorama import Fore, Style
except Exception:  # pragma: no cover
    class _F: GREEN = RED = CYAN = YELLOW = MAGENTA = WHITE = RESET = ""
    class _S: RESET_ALL = ""
    Fore = _F(); Style = _S()

def _ansi24(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def _mix(c1: tuple[int,int,int], c2: tuple[int,int,int], t: float) -> tuple[int,int,int]:
    return (int(_lerp(c1[0], c2[0], t)), int(_lerp(c1[1], c2[1], t)), int(_lerp(c1[2], c2[2], t)))

def _get_rich_type_color(type_name: str, text: str) -> str:
    """Convert type name to Rich markup color format."""
    hex_color = TYPE_COLORS_HEX.get(type_name.lower())
    if not hex_color:
        return text
    return f"[{hex_color}]{text}[/{hex_color}]"

def _hp_bar(cur: int, max_hp: int, width: int = 24) -> str:
    """High-detail HP bar with 24-bit gradient from green→yellow→red.

    Falls back to basic colorama colors if 24-bit not supported (still prints).
    """
    cur = max(0, min(cur, max_hp))
    if max_hp <= 0:
        max_hp = 1
    ratio = cur / max_hp
    filled = int(round(ratio * width))
    filled = max(0, min(filled, width))
    # Colors
    GREEN = (46, 204, 113)
    YELLOW = (241, 196, 15)
    RED = (231, 76, 60)
    blocks: list[str] = []
    for i in range(width):
        t = i / max(width - 1, 1)
        # Map position to color target at current overall HP ratio
        if ratio >= 0.5:
            # 50%..100%: blend YELLOW->GREEN based on ratio
            seg_t = (ratio - 0.5) / 0.5
            col = _mix(YELLOW, GREEN, seg_t)
        else:
            # 0%..50%: blend RED->YELLOW
            seg_t = ratio / 0.5
            col = _mix(RED, YELLOW, seg_t)
        sym = '█' if i < filled else '░'
        blocks.append(f"{_ansi24(*col)}{sym}")
    # Brackets and reset
    bar = ''.join(blocks)
    return f"[{bar}{Style.RESET_ALL}] {cur}/{max_hp}"


def _xp_bar(cur_exp: int, level: int, species_id: int | None, width: int = 24) -> str | None:
    """Render a thin blue EXP progress bar to next level.

    Returns a string like "[━━━━━-----]" with blue fill, or None if insufficient info.
    """
    try:
        if species_id is None or level <= 0:
            return None
        rate = growth_rate(species_id)
        cur_req = required_exp_for_level(level, rate=rate)
        next_req = required_exp_for_level(min(100, level + 1), rate=rate)
        span = max(1, next_req - cur_req)
        progress = max(0, cur_exp - cur_req)
        filled = max(0, min(width, int((progress / span) * width)))
        blue = _ansi24(80, 160, 255)
        filled_str = blue + ("━" * filled) + Style.RESET_ALL
        empty_str = "-" * (width - filled)
        return f"[{filled_str}{empty_str}]"
    except Exception:
        return None


def _status_abbr(status: str | None) -> str:
    """Return bracketed status abbreviation or empty string if none.

    Maps common Gen IV statuses to 3-letter codes: BRN, FRZ, PSN/TOX, PAR, SLP.
    """
    s = (status or "none").lower()
    if s in ("none", "healthy", "ok"):
        return ""
    mapping = {
        "brn": "BRN",
        "frz": "FRZ",
        "psn": "PSN",
        "tox": "TOX",
        "par": "PAR",
        "slp": "SLP",
    }
    ab = mapping.get(s)
    return f" [{ab}]" if ab else ""


def _tty_ok() -> bool:
    try:
        return sys.stdin.isatty() and not bool(os.getenv('PYTEST_CURRENT_TEST'))
    except Exception:
        return False

def _intro_effect_trainer(duration: float = 0.9, fps: int = 18):
    """Speed-line style effect for trainer battles (short and simple)."""
    if not _tty_ok():
        return
    frames = max(1, int(duration * fps))
    cols = 60
    for f in range(frames):
        try:
            tw.clear_screen()
        except Exception:
            pass
        shift = (f * 3) % cols
        line = (" " * shift) + ">>>>>>" + (" " * max(0, cols - shift - 6))
        color = _ansi24(200, 200, 255)
        print(color + line + Style.RESET_ALL)
        print()
        print(color + line + Style.RESET_ALL)
        print()
        print(color + line + Style.RESET_ALL)
        time.sleep(1.0 / fps)

def _intro_effect_wild_grass(duration: float = 1.5, fps: int = 24):
    """Wild encounter effect: rustling grass followed by white flash (DS style)."""
    if not _tty_ok():
        return
    frames = max(1, int(duration * fps))
    width = 70
    height = 10
    
    # Colors
    DARK_GREEN = (30, 100, 30)
    GREEN = (60, 160, 60)
    BRIGHT_GREEN = (90, 200, 90)
    WHITE = (255, 255, 255)
    
    # Split animation: 70% grass rustling, 30% white flash
    grass_frames = int(frames * 0.7)
    flash_frames = frames - grass_frames
    
    for f in range(frames):
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        if f < grass_frames:
            # Grass rustling phase
            progress = f / max(grass_frames - 1, 1)
            intensity = 1.0 + progress * 2.0  # Increase rustling intensity
            
            rows: List[str] = []
            for r in range(height):
                row = [" "] * width
                
                # Generate rustling grass
                grass_count = int(6 + progress * 8)  # More grass over time
                for _ in range(grass_count):
                    # Random position with some wave motion
                    base_x = random.randint(0, width - 1)
                    wave_offset = int(2 * math.sin((f * 0.3) + (r * 0.5)))
                    c = (base_x + wave_offset) % width
                    
                    # Grass blade types
                    blade = random.choice(["^", "/", "\\", "|"])
                    
                    # Color variation based on depth and movement
                    if random.random() < 0.2:
                        color = _ansi24(*BRIGHT_GREEN)
                    elif random.random() < 0.6:
                        color = _ansi24(*GREEN)
                    else:
                        color = _ansi24(*DARK_GREEN)
                    
                    row[c] = color + blade + Style.RESET_ALL
                
                rows.append("".join(row))
            
            print("\n" * 3)  # Top padding
            print("\n".join(rows))
        
        else:
            # White flash phase (like DS games)
            flash_progress = (f - grass_frames) / max(flash_frames - 1, 1)
            
            if flash_progress < 0.3:
                # Bright white flash
                print("\n" * 5)
                white_color = _ansi24(*WHITE)
                flash_line = white_color + "█" * width + Style.RESET_ALL
                for _ in range(height):
                    print(flash_line)
            elif flash_progress < 0.7:
                # Fade to dimmer white
                fade_white = _ansi24(200, 200, 200)
                print("\n" * 5)
                flash_line = fade_white + "█" * width + Style.RESET_ALL
                for _ in range(height):
                    print(flash_line)
            else:
                # Final fade out
                final_white = _ansi24(120, 120, 120)
                print("\n" * 5)
                flash_line = final_white + "░" * width + Style.RESET_ALL
                for _ in range(height):
                    print(flash_line)
        
        time.sleep(1.0 / fps)

def _intro_effect_pokeball_dissolve(duration: float = 1.2, fps: int = 20):
    """Default pre-battle effect: a Poké Ball ASCII that dissolves away.

    Inspired by HG/SS Trainer Red intro. Short, subtle, TTY-only.
    """
    if not _tty_ok():
        return
    frames = max(1, int(duration * fps))
    W, H = 44, 15
    cx, cy = W // 2, H // 2
    rx, ry = W * 0.32, H * 0.42
    center_r = 2.2
    inner_r = 1.2
    # Precompute inside points (ellipse mask)
    inside: List[tuple[int,int]] = []
    for y in range(H):
        for x in range(W):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            if dx*dx + dy*dy <= 1.0:
                inside.append((x, y))
    order = list(range(len(inside)))
    random.shuffle(order)
    # Colors
    RED = (220, 60, 60)
    WHITE = (235, 235, 235)
    BAND = (90, 90, 90)  # dark gray so it shows on dark terminals
    BTN = (250, 250, 250)
    BG = " "
    for f in range(frames):
        try:
            tw.clear_screen()
        except Exception:
            pass
        progress = f / max(frames - 1, 1)
        erase_n = int(progress * len(inside))
        erased_idx = set(order[:erase_n])
        # Build blank canvas
        grid: List[List[str]] = [[BG for _ in range(W)] for _ in range(H)]
        for idx, (x, y) in enumerate(inside):
            if idx in erased_idx:
                continue
            # Determine region color
            dy = y - cy
            # Center button (small circle at center)
            ddx = (x - cx) / 1.3
            ddy = (y - cy) / 1.0
            d2 = ddx*ddx + ddy*ddy
            if d2 <= inner_r*inner_r:
                col = BTN
            elif d2 <= center_r*center_r:
                col = WHITE
            elif abs(dy) <= 1:  # horizontal band
                col = BAND
            else:
                col = RED if y < cy else WHITE
            grid[y][x] = _ansi24(*col) + '█'
        # Render
        out_lines: List[str] = []
        for y in range(H):
            line_parts: List[str] = []
            for x in range(W):
                c = grid[y][x]
                line_parts.append(c)
            out_lines.append("".join(line_parts) + Style.RESET_ALL)
        # Center on screen a bit with top padding
        pad_top = 2
        print("\n" * pad_top + "\n".join(out_lines))
        time.sleep(1.0 / fps)


def _render_state(session: BattleSession):
    """Clear the screen and render a simple battle layout.

    Enemy at top, player near bottom, both with colored HP bars. This gives
    a sense of the HP bar changing each turn.
    """
    try:
        tw.clear_screen()
    except Exception:
        pass
    p = session.player.active()
    e = session.enemy.active()
    # Compute type brackets
    p_types = format_types(p.types)
    e_types = format_types(e.types)
    # Enemy block (trainer or wild)
    if session.is_wild:
        # Wild: match player's outline (name + level + [types] + status on one line; HP bar next line)
        enemy_label = f"{e.name} Lv{e.level} [{e_types}]" + _status_abbr(getattr(e, 'status', None))
        print(enemy_label)
        print(f"   {_hp_bar(e.current_hp or 0, e.stats['hp'])}")
    else:
        enemy_label = f"{e.name} Lv{e.level} [{e_types}]" + _status_abbr(getattr(e, 'status', None))
        print(enemy_label)
        print(f"   {_hp_bar(e.current_hp or 0, e.stats['hp'])}")
    print("\n\n\n")
    # Player block
    player_label = f"{p.name} Lv{p.level} [{p_types}]" + _status_abbr(getattr(p, 'status', None))
    print(player_label)
    print(f"   {_hp_bar(p.current_hp or 0, p.stats['hp'])}")


def _render_polished_battle_frame():
    """Render a stunning battle frame using Rich."""
    # Create beautiful centered title
    title = Text("POKEMON BATTLE", style="bold bright_white")
    title.justify = "center"
    
    # Create panel with double border and centered content
    panel = Panel(
        Align.center(title),
        box=DOUBLE,
        style="bright_white",
        width=100,
        padding=(1, 2)
    )
    console.print(Align.center(panel))

def _render_battle_separator():
    """Render a stylish separator between battle content and menu."""
    try:
        from colorama import Fore, Style
    except Exception:
        class _F: CYAN = BLUE = WHITE = YELLOW = RED = GREEN = MAGENTA = RESET = ""
        class _S: RESET_ALL = BRIGHT = ""
        Fore = _F(); Style = _S()
    
    FRAME_COLOR = Fore.WHITE + Style.BRIGHT
    ACCENT_COLOR = Fore.BLUE + Style.BRIGHT
    
    # Battle area separator
    print(f"{FRAME_COLOR}╠{'═' * 78}╣{Style.RESET_ALL}")
    print(f"{FRAME_COLOR}║{ACCENT_COLOR}{'BATTLE COMMANDS':^78}{FRAME_COLOR}║{Style.RESET_ALL}")
    print(f"{FRAME_COLOR}╠{'═' * 38}╤{'═' * 39}╣{Style.RESET_ALL}")

def _render_battle_footer():
    """Render the bottom border of the battle frame."""
    try:
        from colorama import Fore, Style
    except Exception:
        class _F: CYAN = BLUE = WHITE = YELLOW = RED = GREEN = MAGENTA = RESET = ""
        class _S: RESET_ALL = BRIGHT = ""
        Fore = _F(); Style = _S()
    
    FRAME_COLOR = Fore.CYAN + Style.BRIGHT
    
    print(f"{FRAME_COLOR}╚{'═' * 78}╝{Style.RESET_ALL}")

def _render_hud_inline(session: BattleSession) -> None:
    """Legacy function - redirects to enhanced HUD for compatibility."""
    _render_enhanced_hud_inline(session)

def _render_enhanced_hud_inline(session: BattleSession) -> None:
    """Render a stunning battle HUD using Rich panels and progress bars."""
    try:
        p = session.player.active()
        e = session.enemy.active()
    except Exception:
        return
    
    # Create enemy info with consistent formatting and colored types
    enemy_type_parts = [_get_rich_type_color(t, type_abbreviation(t)) for t in e.types]
    enemy_types = "/".join(enemy_type_parts)
    enemy_info = f"{e.name} Lv{e.level}"
    if hasattr(e, 'status') and e.status:
        enemy_info += f" {_status_abbr(e.status)}"
    
    enemy_hp_text = f"HP: {e.current_hp or 0}/{e.stats['hp']}"
    enemy_hp_bar = _create_hp_bar_rich(e.current_hp or 0, e.stats['hp'])
    
    enemy_panel = Panel(
        f"[bold bright_white]{enemy_info}[/bold bright_white]\n[bright_white][[/bright_white]{enemy_types}[bright_white]][/bright_white]\n[bright_white]{enemy_hp_text}[/bright_white]\n{enemy_hp_bar}",
        title="[bright_white bold]OPPONENT[/bright_white bold]",
        box=ROUNDED,
        style="bright_white",
        width=45,
        padding=(0, 1)
    )
    
    # Create player info with identical formatting and colored types
    player_type_parts = [_get_rich_type_color(t, type_abbreviation(t)) for t in p.types]
    player_types = "/".join(player_type_parts)
    player_info = f"{p.name} Lv{p.level}"
    if hasattr(p, 'status') and p.status:
        player_info += f" {_status_abbr(p.status)}"
    
    player_hp_text = f"HP: {p.current_hp or 0}/{p.stats['hp']}"
    player_hp_bar = _create_hp_bar_rich(p.current_hp or 0, p.stats['hp'])
    
    player_panel = Panel(
        f"[bold bright_white]{player_info}[/bold bright_white]\n[bright_white][[/bright_white]{player_types}[bright_white]][/bright_white]\n[bright_white]{player_hp_text}[/bright_white]\n{player_hp_bar}",
        title="[bright_white bold]YOUR POKEMON[/bright_white bold]",
        box=ROUNDED,
        style="bright_white", 
        width=45,
        padding=(0, 1)
    )
    
    # Display panels side by side with better spacing and centering
    columns = Columns([enemy_panel, player_panel], equal=True, expand=False, padding=(0, 4))
    console.print(Align.center(columns))

def _create_hp_bar_rich(current: int, max_hp: int) -> str:
    """Create a beautiful HP bar using Rich styling."""
    if max_hp <= 0:
        return "[red]FAINTED[/red]"
    
    percent = current / max_hp
    bar_length = 20
    filled = int(percent * bar_length)
    
    # Choose color based on HP percentage
    if percent > 0.5:
        color = "green"
    elif percent > 0.25:
        color = "yellow"
    else:
        color = "red"
    
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{color}]{bar}[/{color}]"

def _enhanced_hp_bar(current: int, max_hp: int, *, enemy: bool = False) -> str:
    """Create an enhanced HP bar with colors and styling."""
    try:
        from colorama import Fore, Style
    except Exception:
        class _F: CYAN = BLUE = WHITE = YELLOW = RED = GREEN = MAGENTA = RESET = ""
        class _S: RESET_ALL = BRIGHT = ""
        Fore = _F(); Style = _S()
    
    if max_hp <= 0:
        return f"{Fore.RED}[FAINTED]{Style.RESET_ALL}"
    
    pct = current / max_hp
    bar_width = 20
    filled = int(pct * bar_width)
    
    # Color based on HP percentage
    if pct > 0.6:
        hp_color = Fore.GREEN
    elif pct > 0.3:
        hp_color = Fore.YELLOW  
    else:
        hp_color = Fore.RED
    
    # Create bar with filled/empty sections
    filled_part = "█" * filled
    empty_part = "░" * (bar_width - filled)
    
    # HP text with numbers
    hp_text = f"{current}/{max_hp}"
    
    return f"{hp_color}[{filled_part}{Fore.WHITE}{empty_part}]{Style.RESET_ALL} {hp_text}"
    """Render enemy and player info + HP bars without clearing the screen.

    Intended to be used under menus via an after-render hook for seamless UX.
    """
    try:
        p = session.player.active()
        e = session.enemy.active()
    except Exception:
        return
    p_types = format_types(p.types)
    e_types = format_types(e.types)
    if session.is_wild:
        enemy_label = f"{e.name} Lv{e.level} [{e_types}]" + _status_abbr(getattr(e, 'status', None))
        print(enemy_label)
        print(f"   {_hp_bar(e.current_hp or 0, e.stats['hp'])}")
    else:
        enemy_label = f"{e.name} Lv{e.level} [{e_types}]" + _status_abbr(getattr(e, 'status', None))
        print(enemy_label)
        print(f"   {_hp_bar(e.current_hp or 0, e.stats['hp'])}")
    print()
    player_label = f"{p.name} Lv{p.level} [{p_types}]" + _status_abbr(getattr(p, 'status', None))
    print(player_label)
    print(f"   {_hp_bar(p.current_hp or 0, p.stats['hp'])}")


def _animate_hp_change(session: BattleSession, target: Battler, old_hp: int, new_hp: int, meta: dict):
    """Animate the HP bar change for the given target in-place.

    Speeds:
    - move effectiveness > 1.0: slightly faster
    - == 1.0: normal
    - < 1.0: slightly slower
    Other causes (status/weather/item/self/recoil/drain): normal speed.
    """
    if not _tty_ok():
        return
    try:
        max_hp = int(target.stats.get('hp', 1))
    except Exception:
        max_hp = 1
    old_hp = max(0, min(int(old_hp), max_hp))
    new_hp = max(0, min(int(new_hp), max_hp))
    if old_hp == new_hp:
        return
    delta = new_hp - old_hp
    total = abs(delta)
    # Compute frame pacing
    base_sleep = 0.02
    if meta.get('cause') == 'move':
        eff = float(meta.get('effectiveness', 1.0) or 1.0)
        if eff > 1.0:
            base_sleep *= 0.7
        elif 0.0 < eff < 1.0:
            base_sleep *= 1.4
        # Play hit SFX at start of damage animation (over music)
        try:
            if delta < 0:  # taking damage
                from pathlib import Path as _Path
                if eff > 1.0:
                    hit = "hit_super_effective.ogg"
                elif 0.0 < eff < 1.0:
                    hit = "hit_weak.ogg"
                else:
                    hit = "hit_normal.ogg"
                sfx = _Path(__file__).resolve().parents[2] / "assets" / "audio" / "sfx" / hit
                audio.play_sfx(str(sfx), volume=1.0)
        except Exception:
            pass
    # Determine steps (cap to keep snappy)
    steps = max(6, min(30, total))
    step_size = max(1, math.ceil(total / steps))
    cur = old_hp
    # Increment/decrement towards new_hp
    while (delta < 0 and cur > new_hp) or (delta > 0 and cur < new_hp):
        cur = cur - step_size if delta < 0 else cur + step_size
        if delta < 0 and cur < new_hp:
            cur = new_hp
        if delta > 0 and cur > new_hp:
            cur = new_hp
        # Temporarily set and render a full state for clarity
        saved = target.current_hp
        try:
            target.current_hp = cur
            _render_state(session)
        finally:
            target.current_hp = saved
        time.sleep(base_sleep)


def _attach_hp_animation(session: BattleSession):
    """Attach hp_change_cb to animate bars during HP changes; returns a restore callable."""
    core = session.core
    prev = getattr(core, 'hp_change_cb', None)
    def _do_wipe_narration(attacker: str, move_name: str):
        if not _tty_ok():
            return
        try:
            tw.clear_screen()
        except Exception:
            pass
        # Typewriter line
        try:
            tw.type_out(f"{attacker} used {move_name}!", speed_setting=3)
        except Exception:
            print(f"{attacker} used {move_name}!")
        # Try move SFX (non-blocking under pytest handled in audio)
        try:
            from pathlib import Path as _Path
            fname = move_name.lower().replace(' ', '-').replace("'", "")
            sfx = _Path(__file__).resolve().parents[2] / "assets" / "audio" / "sfx" / "moves" / f"{fname}.ogg"
            audio.play_sfx_blocking(str(sfx), volume=1.0)
        except Exception:
            pass
        # After SFX, restore HUD
        try:
            tw.clear_screen()
        except Exception:
            pass
        _render_state(session)

    def cb(battler: Battler, old_hp: int, new_hp: int, meta: dict):
        try:
            m = meta or {}
            # For damaging moves, narrate before animating HP (once per action)
            if m.get('cause') == 'move':
                atk = m.get('attacker') or getattr(battler, 'name', None)
                mv = m.get('move')
                # Only narrate on first hit of multi-hit moves
                if atk and mv and int(m.get('hit_index', 1) or 1) == 1:
                    key = (str(atk), str(mv))
                    if getattr(session, '_last_narrated', None) != key:
                        setattr(session, '_last_narrated', key)
                        _do_wipe_narration(str(atk), str(mv))
            _animate_hp_change(session, battler, old_hp, new_hp, m)
        except Exception:
            pass
    core.hp_change_cb = cb
    def restore():
        core.hp_change_cb = prev
    return restore

def _attach_message_overlay(session: BattleSession):
    """Attach a message callback that triggers wipe+SFX narration for non-damaging moves.

    We still chain to previous callback to keep logs for tests.
    """
    core = session.core
    prev = getattr(core, 'message_cb', None)
    def cb(text: str):
        try:
            # Chain to previous logger first
            if prev:
                try:
                    prev(text)
                except Exception:
                    pass
            if _tty_ok():
                # Detect "<Name> used <Move>!" lines
                m = re.match(r"^(.+?) used (.+?)!", text)
                if m:
                    atk, mv = m.group(1), m.group(2)
                    key = (atk, mv)
                    if getattr(session, '_last_narrated', None) != key:
                        setattr(session, '_last_narrated', key)
                        # Wipe + SFX, then restore HUD (for status/non-damaging messages)
                        try:
                            tw.clear_screen()
                        except Exception:
                            pass
                        try:
                            tw.type_out(f"{atk} used {mv}!", speed_setting=3)
                        except Exception:
                            print(f"{atk} used {mv}!")
                        try:
                            from pathlib import Path as _Path
                            fname = mv.lower().replace(' ', '-').replace("'", "")
                            sfx = _Path(__file__).resolve().parents[2] / "assets" / "audio" / "sfx" / "moves" / f"{fname}.ogg"
                            audio.play_sfx_blocking(str(sfx), volume=1.0)
                        except Exception:
                            pass
                        try:
                            tw.clear_screen()
                        except Exception:
                            pass
                        _render_state(session)
                else:
                    # Show important follow-up effect messages and pause to read.
                    txt = str(text)
                    show_and_pause = False
                    try:
                        # Stat stage changes (e.g., "Defense fell!") or cures/status
                        if txt.endswith(" fell!") or txt.endswith(" rose!"):
                            show_and_pause = True
                        elif txt.startswith("But nothing happened"):
                            show_and_pause = True
                        elif "is afflicted with" in txt:
                            show_and_pause = True
                    except Exception:
                        show_and_pause = False
                    if show_and_pause:
                        try:
                            tw.type_out(txt, speed_setting=2)
                        except Exception:
                            print(txt)
                        # Removed manual prompt for smoother battle flow
                        try:
                            tw.clear_screen()
                        except Exception:
                            pass
                        _render_state(session)
        except Exception:
            pass
    core.message_cb = cb
    def restore():
        core.message_cb = prev
    return restore


def _enemy_move_index(e: Battler, rng: random.Random) -> int:
    usable = [i for i, m in enumerate(e.moves) if m.max_pp == 0 or m.pp > 0]
    if not usable:
        return 0
    return rng.choice(usable)

def _next_available_index(party: Party, skip_index: int | None = None) -> int | None:
    try:
        for i, m in enumerate(party.members):
            if skip_index is not None and i == skip_index:
                continue
            if (m.current_hp or 0) > 0:
                return i
    except Exception:
        pass
    return None

def _forced_switch_player(session: BattleSession) -> bool:
    """Force the player to choose a replacement when their active fainted.

    Returns True if a switch occurred, False if none available (no action).
    """
    alive_items: List[MenuItem] = []
    cur_idx = session.player.active_index
    for i, b in enumerate(session.player.members):
        if (b.current_hp or 0) <= 0 or i == cur_idx:
            continue
        hp_bar = _hp_bar(b.current_hp or 0, b.stats['hp'])
        alive_items.append(MenuItem(label=f"{b.name} Lv{b.level} {hp_bar}", value=str(i)))
    if not alive_items:
        return False
    m = Menu(
        "Choose a Pokémon to send out",
        alive_items,
        allow_escape=False,
        footer="Enter send out",
        after_render=lambda: _render_hud_inline(session),
    )
    sel = m.run()
    try:
        if sel is not None:
            session.player.active_index = int(sel)
            print(f"Go! {session.player.active().name}!")
            return True
    except Exception:
        pass
    # Non-interactive fallback: auto switch first available
    nxt = _next_available_index(session.player, skip_index=cur_idx)
    if nxt is not None:
        session.player.active_index = nxt
        print(f"Go! {session.player.active().name}!")
        return True
    return False


def _choose_move(session: BattleSession) -> int | None:
    """Beautiful move selection using Rich menus with colored types."""
    p = session.player.active()
    if not p.moves:
        return 0
    
    # Create menu items with colored types and detailed info
    items: List[MenuItem] = []
    for i, mv in enumerate(p.moves):
        pp_txt = f"{mv.pp}/{mv.max_pp}" if mv.max_pp else "--"
        disabled = (mv.max_pp > 0 and mv.pp <= 0)
        t_abbr = type_abbreviation(mv.type)
        
        # Get power display
        power_display = str(getattr(mv, 'power', '--'))
        
        # Create detailed menu item with type color, PP, and power
        type_colored = _get_rich_type_color(mv.type, t_abbr)
        
        # Style PP based on remaining uses
        if disabled:
            pp_style = "red"
        elif mv.pp <= mv.max_pp * 0.25:
            pp_style = "yellow" 
        else:
            pp_style = "green"
        
        # Create comprehensive label with all info
        label = f"{mv.name} | {type_colored} | PP: [{pp_style}]{pp_txt}[/{pp_style}] | Power: {power_display}"
        items.append(MenuItem(label=label, value=str(i), disabled=disabled))
    
    # Add cancel option
    items.append(MenuItem(label="Cancel", value="__cancel__"))
    
    # Custom full render function that renders everything together
    def render_complete_move_ui():
        # Clear and render the entire interface
        console.clear()
        
        # Add some top spacing
        console.print()
        
        # Render centered battle frame
        _render_polished_battle_frame()
        
        # Add spacing between title and Pokemon info
        console.print()
        
        # Render Pokemon information
        _render_enhanced_hud_inline(session)
        
        # Add spacing between Pokemon info and move selection
        console.print()
        
        # Now render the menu manually with arrows and colored types
        from platinum.ui.menu_nav import get_menu_color
        menu_color = get_menu_color()
        
        # Create beautiful Rich-powered menu
        menu_table = Table(
            title=f"[bold {menu_color}]SELECT MOVE[/bold {menu_color}]",
            box=ROUNDED,
            show_header=False,
            style="bright_white",
            title_style=f"bold {menu_color}",
            width=80
        )
        
        menu_table.add_column("Option", style="bright_white", justify="left")
        
        for i, item in enumerate(items):
            # Create styled menu item with very clear pointer
            if i == menu.index:
                if item.disabled:
                    prefix = f"[{menu_color}]►[/{menu_color}] [dim red]"
                    suffix = "[/dim red]"
                else:
                    prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                    suffix = f"[/{menu_color}]"
            else:
                if item.disabled:
                    prefix = "  [dim]"
                    suffix = "[/dim]"
                else:
                    prefix = "  [bright_white]"
                    suffix = "[/bright_white]"
            
            # Handle disabled items
            if item.disabled:
                display_label = f"[X] {item.label}"
            else:
                display_label = item.label
            
            full_label = f"{prefix}{display_label}{suffix}"
            menu_table.add_row(full_label)
        
        # Display the menu
        console.print(Align.center(menu_table))
        
        # Footer
        from rich.panel import Panel
        footer_panel = Panel(
            "↑/↓ W/S • Enter to use move • Esc to go back",
            style="dim bright_white",
            box=ROUNDED
        )
        console.print(footer_panel)
    
    menu = Menu(
        f"{p.name}'s Moves",
        items,
        allow_escape=True,
        footer="↑/↓ W/S • Enter to use move • Esc to go back",
        full_render=render_complete_move_ui,
    )
    res = menu.run()
    
    if res is None or res == "__cancel__":
        return None
    return int(res)


def run_battle_ui(session: BattleSession, *, is_trainer: bool = False, trainer_label: Optional[str] = None, rng: Optional[random.Random] = None, inventory: Optional[Dict[str,int]] = None, ctx=None) -> str:
    rng = rng or random.Random()
    from platinum.system.settings import Settings
    if getattr(Settings.load().data, 'debug', False):
        print(f"[battle] Starting {'trainer' if is_trainer else 'wild'} battle!")
    # Snapshot currently playing music to restore after battle (especially for wild encounters)
    prev_music: Optional[str] = None
    try:
        prev_music = getattr(audio, "_state").last_path
    except Exception:
        prev_music = None
    # Safety: ensure rival theme plays if this is a Rival trainer battle; otherwise play default wild BGM
    if is_trainer and (trainer_label or '').lower().startswith('rival'):
        try:
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            
            # Check for intro+loop files first
            rival_intro = root / "assets" / "audio" / "bgm" / "battle_rival_intro.ogg"
            rival_loop = root / "assets" / "audio" / "bgm" / "battle_rival_loop.ogg"
            
            if rival_intro.exists() and rival_loop.exists():
                audio.play_intro_loop_music(str(rival_intro), str(rival_loop))
            else:
                # Fallback to single file
                rival_bgm = root / "assets" / "audio" / "bgm" / "battle_rival.ogg"
                audio.play_music(str(rival_bgm), loop=True)
            
            audio.set_music_volume(0.7)
        except Exception:
            pass
    elif not is_trainer:
        try:
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            
            # Check for intro+loop files first
            wild_intro = root / "assets" / "audio" / "bgm" / "wild_battle_intro.ogg"
            wild_loop = root / "assets" / "audio" / "bgm" / "wild_battle_loop.ogg"
            
            if wild_intro.exists() and wild_loop.exists():
                audio.play_intro_loop_music(str(wild_intro), str(wild_loop))
            else:
                # Fallback to single file
                wild_bgm = root / "assets" / "audio" / "bgm" / "wild_battle.ogg"
                audio.play_music(str(wild_bgm), loop=True)
            
            audio.set_music_volume(0.7)
        except Exception:
            pass
    # Show level cap if present on active battler
    active = session.player.active()
    badge_count = getattr(active, 'badge_count', None)
    if badge_count is not None and badge_count < 8:
        from platinum.battle.obedience import level_cap_for_badges
        cap = level_cap_for_badges(badge_count)
        if getattr(Settings.load().data, 'debug', False):
            if active.level > cap:
                print(f"(Warning: {active.name} may disobey; badge cap Lv{cap})")
            else:
                print(f"(Current obedience cap: Lv{cap})")
    # For wild battles, keep raw species name; intro text will say "You encountered a wild X!"
    # Pre-battle screen effect - different for wild vs trainer battles
    if is_trainer:
        _intro_effect_pokeball_dissolve()
    else:
        _intro_effect_wild_grass()
    # Trainer intro sequence
    if is_trainer:
        try:
            tw.clear_screen()
        except Exception:
            pass
        who = trainer_label or "Trainer"
        tw.type_out(f"You are challenged by {who}!", speed_setting=3)
        time.sleep(2)
        try:
            tw.clear_screen()
        except Exception:
            pass
        tw.type_out(f"Go {session.player.active().name}!", speed_setting=3)
        time.sleep(2)
    else:
        # Wild intro sequence
        try:
            tw.clear_screen()
        except Exception:
            pass
        try:
            wild_name = session.enemy.active().name
        except Exception:
            wild_name = "Pokémon"
        tw.type_out(f"You encountered a wild {wild_name}!", speed_setting=3)
        time.sleep(2)
        try:
            tw.clear_screen()
        except Exception:
            pass
        tw.type_out(f"Go {session.player.active().name}!", speed_setting=3)
        time.sleep(2)
    # Attach HP animation callback for the duration of the battle
    _restore_hp_cb = _attach_hp_animation(session)
    _restore_msg_cb = _attach_message_overlay(session)
    try:
        while not session.is_over():
            # Menu items for navigation
            main_items = [
                MenuItem("Fight", "fight"),
                MenuItem("Pokemon", "pokemon"),
                MenuItem("Bag", "bag"),
                MenuItem("Run", "run", disabled=is_trainer),
            ]
            
            # Custom full render function that renders everything together
            def render_complete_battle_ui():
                # Clear and render the entire battle interface
                console.clear()
                
                # Add some top spacing
                console.print()
                
                # Render centered battle frame
                _render_polished_battle_frame()
                
                # Add spacing between title and Pokemon info
                console.print()
                
                # Render Pokemon information
                _render_enhanced_hud_inline(session)
                
                # Add spacing between Pokemon info and battle commands
                console.print()
                
                # Now render the menu manually
                from platinum.ui.menu_nav import get_menu_color
                menu_color = get_menu_color()
                
                # Create beautiful Rich-powered menu
                from rich.table import Table
                from rich.align import Align
                menu_table = Table(
                    title=f"[bold {menu_color}]BATTLE COMMANDS[/bold {menu_color}]",
                    box=ROUNDED,
                    show_header=False,
                    style="bright_white",
                    title_style=f"bold {menu_color}",
                    width=60
                )
                
                menu_table.add_column("Option", style="bright_white", justify="left")
                
                for i, item in enumerate(main_items):
                    # Create styled menu item with very clear pointer
                    if i == menu.index:
                        if item.disabled:
                            style_open, style_close = "[dim red]", "[/dim red]"
                            prefix = f"[{menu_color}]►[/{menu_color}] "
                        else:
                            style_open, style_close = f"[{menu_color}]", f"[/{menu_color}]"
                            prefix = f"[{menu_color}]►[/{menu_color}] "
                    else:
                        if item.disabled:
                            style_open, style_close = "[dim]", "[/dim]"
                            prefix = "  "
                        else:
                            style_open, style_close = "[bright_white]", "[/bright_white]"
                            prefix = "  "
                    
                    label = f"[X] {item.label}" if item.disabled else item.label
                    
                    # Use custom color if provided
                    if item.label_color:
                        full_label = f"{prefix}{item.label_color}{label}[/]"
                    else:
                        full_label = f"{prefix}{style_open}{label}{style_close}"
                    
                    menu_table.add_row(full_label)
                
                # Display the menu
                console.print(Align.center(menu_table))
                
                # Footer
                from rich.panel import Panel
                footer_panel = Panel(
                    "↑/↓ W/S • Enter select • Choose your strategy!",
                    style="dim bright_white",
                    box=ROUNDED
                )
                console.print(footer_panel)
            
            menu = Menu(
                "BATTLE COMMANDS",
                main_items,
                allow_escape=False,
                footer="↑/↓ W/S • Enter select • Choose your strategy!",
                full_render=render_complete_battle_ui,
            )
            choice = menu.run()
            
            # Add footer after menu
            _render_battle_footer()
            if choice == "fight":
                mv_idx = _choose_move(session)
                if mv_idx is None:
                    continue  # back out
                enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                pre_turn_log_len = len(session.log)
                session.step(player_move_idx=mv_idx, enemy_move_idx=enemy_idx)
                # For non-TTY (tests), print the new messages.
                if not _tty_ok():
                    new_msgs = session.log[pre_turn_log_len:]
                    for msg in new_msgs:
                        print(msg)
                # Redraw HUD after step
                if _tty_ok():
                    _render_state(session)
                # After messages, handle faint sequence properly:
                # 1. Check for faints
                # 2. Apply XP/EV immediately for each faint
                # 3. Handle replacements
                # 4. Check for battle end
                
                # Check enemy faint first (player gets XP when enemy faints)
                enemy_fainted = False
                enemy_species = None
                enemy_level = None
                try:
                    e_act = session.enemy.active()
                    if e_act and (e_act.current_hp or 0) <= 0:
                        enemy_fainted = True
                        enemy_species = getattr(e_act, 'species_id', 1)  # fallback species
                        enemy_level = e_act.level
                        # Store faint info for XP application (since ctx not available in this function)
                        setattr(session, '_fainted_enemies', getattr(session, '_fainted_enemies', []))
                        getattr(session, '_fainted_enemies').append((enemy_species, enemy_level, is_trainer))
                except Exception:
                    pass
                
                # Check player faint
                player_fainted = False
                try:
                    p_act = session.player.active()
                    if p_act and (p_act.current_hp or 0) <= 0:
                        player_fainted = True
                except Exception:
                    pass
                
                # Handle player replacement if needed
                if player_fainted:
                    if not _forced_switch_player(session):
                        # No available Pokémon -> player loses
                        print("You have no remaining Pokémon!")
                        print("PLAYER blacked out!")
                        return "PLAYER_LOSS"
                
                # Handle enemy replacement if needed (trainer battles only)
                if enemy_fainted and is_trainer:
                    nxt_idx = _next_available_index(session.enemy, skip_index=session.enemy.active_index)
                    if nxt_idx is not None:
                        nxt_name = session.enemy.members[nxt_idx].name
                        who = trainer_label or "Trainer"
                        prompt_items = [
                            MenuItem("Yes", value="yes"),
                            MenuItem("No", value="no"),
                        ]
                        choice_sw = Menu(
                            f"{who} is about to send in {nxt_name}. Switch Pokémon?",
                            prompt_items,
                            allow_escape=True,
                            after_render=lambda: _render_hud_inline(session),
                        ).run()
                        if choice_sw == "yes":
                            _forced_switch_player(session)
                        # Send in next enemy Pokémon
                        session.enemy.active_index = nxt_idx
                        print(f"{who} sent out {session.enemy.active().name}!")
            elif choice == "pokemon":
                # Create menu items for Pokemon team
                party_items: List[MenuItem] = []
                for i, b in enumerate(session.player.members):
                    disabled = (b.current_hp or 0) <= 0 and i != session.player.active_index
                    
                    # Status indicators for menu label
                    if i == session.player.active_index:
                        status_text = "(ACTIVE)"
                    elif (b.current_hp or 0) <= 0:
                        status_text = "(FAINTED)"
                    else:
                        status_text = ""
                    
                    # Create enhanced menu label with types and HP
                    type_parts = [_get_rich_type_color(t, type_abbreviation(t)) for t in b.types]
                    types_display = "/".join(type_parts)
                    hp_ratio = f"{b.current_hp or 0}/{b.stats['hp']}"
                    
                    label = f"{b.name} Lv{b.level} | {types_display} | HP: {hp_ratio} {status_text}"
                    party_items.append(MenuItem(label=label, value=str(i), disabled=disabled))
                
                party_items.append(MenuItem("Cancel", "__cancel__"))
                
                # Custom full render function
                def render_complete_pokemon_ui():
                    console.clear()
                    
                    # Add some top spacing
                    console.print()
                    
                    # Render centered battle frame
                    _render_polished_battle_frame()
                    
                    # Add spacing between title and Pokemon info
                    console.print()
                    
                    # Render Pokemon information
                    _render_enhanced_hud_inline(session)
                    
                    # Add spacing between Pokemon info and team selection
                    console.print()
                    
                    # Now render the menu manually with arrows and colored types
                    from platinum.ui.menu_nav import get_menu_color
                    menu_color = get_menu_color()
                    
                    # Create beautiful Rich-powered menu
                    menu_table = Table(
                        title=f"[bold {menu_color}]CHOOSE POKEMON[/bold {menu_color}]",
                        box=ROUNDED,
                        show_header=False,
                        style="bright_white",
                        title_style=f"bold {menu_color}",
                        width=80
                    )
                    
                    menu_table.add_column("Option", style="bright_white", justify="left")
                    
                    for i, item in enumerate(party_items):
                        # Create styled menu item with very clear pointer
                        if i == pokemon_menu.index:
                            if item.disabled:
                                prefix = f"[{menu_color}]►[/{menu_color}] [dim red]"
                                suffix = "[/dim red]"
                            else:
                                prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                                suffix = f"[/{menu_color}]"
                        else:
                            if item.disabled:
                                prefix = "  [dim]"
                                suffix = "[/dim]"
                            else:
                                prefix = "  [bright_white]"
                                suffix = "[/bright_white]"
                        
                        # Handle disabled items
                        if item.disabled:
                            display_label = f"[X] {item.label}"
                        else:
                            display_label = item.label
                        
                        full_label = f"{prefix}{display_label}{suffix}"
                        menu_table.add_row(full_label)
                    
                    # Display the menu
                    console.print(Align.center(menu_table))
                    
                    # Footer
                    from rich.panel import Panel
                    footer_panel = Panel(
                        "↑/↓ W/S • Enter to select • Esc to go back",
                        style="dim bright_white",
                        box=ROUNDED
                    )
                    console.print(footer_panel)
                
                pokemon_menu = Menu(
                    "Choose Pokemon",
                    party_items,
                    allow_escape=True,
                    footer="↑/↓ W/S • Enter to select • Esc to go back",
                    full_render=render_complete_pokemon_ui,
                )
                sel = pokemon_menu.run()
                
                if sel and sel != "__cancel__":
                    idx = int(sel)
                    pokemon = session.player.members[idx]
                    
                    # Create submenu options
                    can_switch = idx != session.player.active_index and (pokemon.current_hp or 0) > 0
                    sub_items = [
                        MenuItem("Switch", "switch", disabled=not can_switch),
                        MenuItem("Check Summary", "summary"),
                        MenuItem("Cancel", "cancel"),
                    ]
                    
                    # Simple submenu for now - can enhance later
                    sub = Menu(
                        f"{pokemon.name} Options",
                        sub_items,
                        allow_escape=True,
                    ).run()
                    
                    if sub == "switch":
                        session.player.active_index = idx
                        console.print(f"[green]Go! {session.player.active().name}![/green]")
                        time.sleep(1)
                    elif sub == "summary":
                        input(f"\n{pokemon.name} Summary - Press Enter to continue...")
                continue
            elif choice == "bag":
                inv = inventory or {}
                
                def _fmt(name: str, count: int) -> str:
                    return f"{name.replace('-', ' ').title()} ×{count}"
                
                # Clean pocket categories
                pockets = [
                    ("Items", lambda n: n in {"repel", "escape-rope", "x-attack", "x-defend"}),
                    ("Medicine", lambda n: n in {"potion", "super-potion", "antidote", "paralyze-heal", "ether"}),
                    ("Poke Balls", lambda n: n.endswith("ball")),
                    ("TMs & HMs", lambda n: n.startswith("tm") or n.startswith("hm")),
                    ("Berries", lambda n: n.endswith("berry")),
                    ("Key Items", lambda n: n in {"town-map", "old-rod", "works-key"}),
                ]
                
                # Create pocket menu items
                pocket_items = [MenuItem(p[0], p[0]) for p in pockets]
                pocket_items.append(MenuItem("Cancel", "__cancel__"))
                
                # Custom full render function for bag
                def render_complete_bag_ui():
                    console.clear()
                    
                    # Add some top spacing
                    console.print()
                    
                    # Render centered battle frame
                    _render_polished_battle_frame()
                    
                    # Add spacing between title and Pokemon info
                    console.print()
                    
                    # Render Pokemon information
                    _render_enhanced_hud_inline(session)
                    
                    # Add spacing between Pokemon info and bag selection
                    console.print()
                    
                    # Now render the menu manually with arrows
                    from platinum.ui.menu_nav import get_menu_color
                    menu_color = get_menu_color()
                    
                    # Create beautiful Rich-powered menu
                    menu_table = Table(
                        title=f"[bold {menu_color}]CHOOSE POCKET[/bold {menu_color}]",
                        box=ROUNDED,
                        show_header=False,
                        style="bright_white",
                        title_style=f"bold {menu_color}",
                        width=60
                    )
                    
                    menu_table.add_column("Option", style="bright_white", justify="left")
                    
                    for i, item in enumerate(pocket_items):
                        # Create styled menu item with very clear pointer
                        if i == pocket_menu.index:
                            prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                            suffix = f"[/{menu_color}]"
                        else:
                            prefix = "  [bright_white]"
                            suffix = "[/bright_white]"
                        
                        full_label = f"{prefix}{item.label}{suffix}"
                        menu_table.add_row(full_label)
                    
                    # Display the menu
                    console.print(Align.center(menu_table))
                    
                    # Footer
                    from rich.panel import Panel
                    footer_panel = Panel(
                        "↑/↓ W/S • Enter to open • Esc to go back",
                        style="dim bright_white",
                        box=ROUNDED
                    )
                    console.print(footer_panel)
                
                pocket_menu = Menu(
                    "Choose Pocket",
                    pocket_items,
                    allow_escape=True,
                    footer="↑/↓ W/S • Enter to open • Esc to go back",
                    full_render=render_complete_bag_ui,
                )
                psel = pocket_menu.run()
                
                if not psel or psel == "__cancel__":
                    continue
                
                pocket = next((p for p in pockets if p[0]==psel), None)
                if not pocket:
                    continue
                
                # Build item list for the chosen pocket
                filt = pocket[1]
                items_in_pocket = [(n,c) for n,c in sorted(inv.items()) if c>0 and filt(n)]
                
                if "Poke Balls" in psel and not session.is_wild:
                    console.print(f"[red]You can't use that here.[/red]")
                    time.sleep(1)
                    continue
                
                if not items_in_pocket:
                    console.print(f"[yellow](Nothing here)[/yellow]")
                    time.sleep(1)
                    continue
                
                # Create item menu
                item_items = [MenuItem(f"{_fmt(n,c)}", n) for n, c in items_in_pocket]
                item_items.append(MenuItem("Cancel", "__cancel__"))
                
                # Custom full render function for items
                def render_complete_item_ui():
                    console.clear()
                    
                    # Add some top spacing
                    console.print()
                    
                    # Render centered battle frame
                    _render_polished_battle_frame()
                    
                    # Add spacing between title and Pokemon info
                    console.print()
                    
                    # Render Pokemon information
                    _render_enhanced_hud_inline(session)
                    
                    # Add spacing between Pokemon info and item selection
                    console.print()
                    
                    # Now render the menu manually with arrows
                    from platinum.ui.menu_nav import get_menu_color
                    menu_color = get_menu_color()
                    
                    # Create beautiful Rich-powered menu
                    menu_table = Table(
                        title=f"[bold {menu_color}]{(psel or 'ITEMS').upper()}[/bold {menu_color}]",
                        box=ROUNDED,
                        show_header=False,
                        style="bright_white",
                        title_style=f"bold {menu_color}",
                        width=60
                    )
                    
                    menu_table.add_column("Option", style="bright_white", justify="left")
                    
                    for i, item in enumerate(item_items):
                        # Create styled menu item with very clear pointer
                        if i == item_menu.index:
                            prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                            suffix = f"[/{menu_color}]"
                        else:
                            prefix = "  [bright_white]"
                            suffix = "[/bright_white]"
                        
                        full_label = f"{prefix}{item.label}{suffix}"
                        menu_table.add_row(full_label)
                    
                    # Display the menu
                    console.print(Align.center(menu_table))
                    
                    # Footer
                    footer_panel = Panel(
                        "↑/↓ W/S • Enter to use • Esc to go back",
                        style="dim bright_white",
                        box=ROUNDED
                    )
                    console.print(footer_panel)
                
                item_menu = Menu(
                    f"{psel}",
                    item_items,
                    allow_escape=True,
                    footer="↑/↓ W/S • Enter to use • Esc to go back",
                    full_render=render_complete_item_ui,
                )
                sel = item_menu.run()
                
                if not sel or sel == "__cancel__":
                    continue
                
                # Item usage logic
                if sel in {"potion", "super-potion"}:
                    heal_amt = 20 if sel == "potion" else 50
                    target = session.player.active()
                    if (target.current_hp or 0) >= target.stats['hp']:
                        console.print(f"[yellow]It won't have any effect.[/yellow]")
                        time.sleep(1)
                        continue  # Stay in bag menu
                    else:
                        heal = min(heal_amt, target.stats['hp'] - (target.current_hp or 0))
                        session.core.apply_heal(target, heal, cause='item', meta={'item': sel})
                        inv[sel] -= 1
                        console.print(f"[green]Restored {heal} HP to {target.name}![/green]")
                        time.sleep(2)
                        
                        # This counts as the player's turn, so enemy gets to move
                        enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                        pre_turn_log_len = len(session.log)
                        session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
                        
                        # For non-TTY (tests), print the new messages
                        if not _tty_ok():
                            new_msgs = session.log[pre_turn_log_len:]
                            for msg in new_msgs:
                                print(msg)
                        
                        # Exit bag menu and return to main battle menu
                        break
                        
                elif sel in {"antidote", "paralyze-heal", "burn-heal", "ice-heal", "awakening"}:
                    target = session.player.active()
                    target_status = getattr(target, 'status', None)
                    
                    # Check if item can cure the current status
                    can_cure = False
                    if sel == "antidote" and target_status == "poison":
                        can_cure = True
                    elif sel == "paralyze-heal" and target_status == "paralysis":
                        can_cure = True
                    elif sel == "burn-heal" and target_status == "burn":
                        can_cure = True
                    elif sel == "ice-heal" and target_status == "freeze":
                        can_cure = True
                    elif sel == "awakening" and target_status == "sleep":
                        can_cure = True
                    
                    if not target_status or not can_cure:
                        console.print(f"[yellow]It won't have any effect.[/yellow]")
                        time.sleep(1)
                        continue  # Stay in bag menu
                    else:
                        # Cure the status condition using the core method
                        session.core._cure_status(target, announce=False)
                        inv[sel] -= 1
                        console.print(f"[green]{target.name} was cured of {target_status}![/green]")
                        time.sleep(2)
                        
                        # This counts as the player's turn, so enemy gets to move
                        enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                        pre_turn_log_len = len(session.log)
                        session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
                        
                        # For non-TTY (tests), print the new messages
                        if not _tty_ok():
                            new_msgs = session.log[pre_turn_log_len:]
                            for msg in new_msgs:
                                print(msg)
                        
                        # Exit bag menu and return to main battle menu
                        break
                        
                elif sel.endswith("ball"):
                    if session.is_wild:
                        result = session.attempt_capture(ball=sel)
                        inv[sel] -= 1
                        if result == 'CAPTURED':
                            console.print("[green]Gotcha! Pokémon captured![/green]")
                            try:
                                _play_victory_music(is_trainer=False)
                            except Exception:
                                pass
                            input("Press Enter to continue...")
                            try:
                                audio.stop_music()
                            except Exception:
                                pass
                            return 'PLAYER_WIN'
                        else:
                            console.print(f"[yellow]{result.replace('_', ' ').title()}[/yellow]")
                            time.sleep(2)
                            
                            # Failed capture counts as a turn, enemy gets to move
                            enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                            pre_turn_log_len = len(session.log)
                            session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
                            
                            # For non-TTY (tests), print the new messages
                            if not _tty_ok():
                                new_msgs = session.log[pre_turn_log_len:]
                                for msg in new_msgs:
                                    print(msg)
                            
                            # Exit bag menu and return to main battle menu
                            break
                    else:
                        console.print("[red]You can't use that here.[/red]")
                        time.sleep(1)
                        continue  # Stay in bag menu
                else:
                    console.print("[yellow]Nothing happened.[/yellow]")
                    time.sleep(1)
                    continue  # Stay in bag menu
            elif choice == "run":
                # Enhanced run option with styling
                try:
                    from colorama import Fore, Style
                except Exception:
                    class _RunFore: CYAN = BLUE = WHITE = YELLOW = RED = GREEN = MAGENTA = RESET = ""
                    class _RunStyle: RESET_ALL = BRIGHT = ""
                    Fore = _RunFore(); Style = _RunStyle()
                
                if is_trainer:
                    print(f"{Fore.RED + Style.BRIGHT}You can't run from a trainer battle!{Style.RESET_ALL}")
                else:
                    if session.attempt_flee():
                        print(f"{Fore.GREEN + Style.BRIGHT}Got away safely!{Style.RESET_ALL}")
                        # Stop battle music and resume overworld
                        try:
                            audio.stop_music()
                        except Exception:
                            pass
                        if prev_music:
                            try:
                                audio.play_music(prev_music, loop=True)
                            except Exception:
                                pass
                        return "ESCAPE"
                    else:
                        print(f"{Fore.YELLOW}Couldn't escape!{Style.RESET_ALL}")
                        enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                        session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
            else:
                continue
        outcome = session.outcome()
    finally:
        # Restore previous HP callback (avoid leaking to other battles)
        try:
            _restore_hp_cb()
        except Exception:
            pass
        
    # Handle wild battle victory sequence
    if outcome == "PLAYER_WIN" and session.is_wild and not is_trainer:
        try:
            # Get defeated enemy info for XP calculation
            enemy_battler = session.enemy.active()
            enemy_species = enemy_battler.species_id
            enemy_level = enemy_battler.level
            
            # Run wild victory sequence with XP, level-ups, and music
            _wild_battle_victory_sequence(ctx=ctx, session=session, 
                                        fainted_pokemon_species=enemy_species, 
                                        fainted_pokemon_level=enemy_level,
                                        previous_music=prev_music)
        except Exception as e:
            if getattr(Settings.load().data, 'debug', False):
                print(f"[battle] Wild victory sequence error: {e}")
            # Fallback: just play victory music and stop it
            try:
                _play_victory_music(is_trainer=False)
                time.sleep(2)
                audio.stop_music()
            except Exception:
                pass
                
    # Post-battle audio and messages
    try:
        if outcome == 'ESCAPE' and session.is_wild and not is_trainer and prev_music:
            # Wild escape: restore route music (victory handled above)
            audio.play_music(prev_music, loop=True)
    except Exception:
        pass
    # Battle outcome logging (removed user prompts for smoother flow)
    if getattr(Settings.load().data, 'debug', False):
        print(f"[battle] Battle ended: {outcome}")
    return outcome

def _play_victory_music(is_trainer: bool, victory_music: Optional[str] = None):
    """Play appropriate victory music for battle type as BGM."""
    try:
        audio.stop_music()
    except Exception:
        pass
    
    if is_trainer:
        music_file = victory_music or "victory_trainer_battle"
    else:
        music_file = "victory_wild_battle"
    
    try:
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        
        # Check for intro+loop files first
        intro_path = root / "assets" / "audio" / "bgm" / f"{music_file}_intro.ogg"
        loop_path = root / "assets" / "audio" / "bgm" / f"{music_file}_loop.ogg"
        
        if intro_path.exists() and loop_path.exists():
            # Use intro+loop system for seamless victory music
            audio.play_intro_loop_music(str(intro_path), str(loop_path))
        else:
            # Fallback to single file (non-looping for victory music)
            audio.play_music(f"assets/audio/bgm/{music_file}.ogg", loop=False)
    except Exception:
        pass

def _wild_battle_victory_sequence(ctx, session, fainted_pokemon_species: int, fainted_pokemon_level: int, previous_music: Optional[str] = None):
    """Handle wild battle victory sequence with XP, level-ups, and proper music flow."""
    from platinum.ui import typewriter as tw
    
    try:
        # Apply XP and handle level-ups for wild battle victory
        _apply_exp_on_faint(ctx, session, fainted_pokemon_species, fainted_pokemon_level, is_trainer=False)
        
        # Play wild victory music after all XP/level-ups are done
        _play_victory_music(is_trainer=False)
        
        # Victory text with typewriter
        try:
            tw.clear_screen()
            tw.type_out("You won the battle!")
        except Exception:
            print("You won the battle!")
        
        print("Press Enter to continue...")
        try:
            input()
        except Exception:
            pass
        
        # Stop victory music and prepare to resume overworld
        try:
            audio.stop_music()
        except Exception:
            pass
        
        # Clear screen and resume previous music if available
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        # Resume previous music (usually route music)
        if previous_music and previous_music.endswith('.ogg'):
            try:
                import time
                time.sleep(0.1)
                audio.stop_music()
                time.sleep(0.1)
                audio.play_music(previous_music, loop=True)
                audio.set_music_volume(0.7)
            except Exception:
                pass
        else:
            try:
                audio.stop_music()
            except Exception:
                pass
                
    except Exception as e:
        print(f"Error in wild victory sequence: {e}")

def _apply_exp_on_faint(ctx, session, fainted_pokemon_species: int, fainted_pokemon_level: int, *, is_trainer: bool = False):
    """Apply XP immediately when a Pokemon faints (per proper battle sequence)."""
    try:
        from platinum.battle.experience import exp_gain, apply_experience, growth_rate, required_exp_for_level
        from platinum.battle.factory import derive_stats
        from platinum.data.species_lookup import species_id
        from platinum.data.loader import get_species, level_up_learnset
        from platinum.ui.menu_nav import Menu, MenuItem
        from platinum.ui import typewriter as tw
        import time
        
        # Determine participants (active battlers)
        try:
            part_indices = set(getattr(session, 'player_participants', {session.player.active_index}))
        except Exception:
            part_indices = {session.player.active_index}
        participants = max(1, len(part_indices))
        
        def _sid_for(val):
            try:
                return species_id(val) if isinstance(val, str) else int(val)
            except Exception:
                return None
        
        # Calculate and apply XP gains for all party members
        for idx, pm in enumerate(ctx.state.party):
            is_part = idx in part_indices
            gained_xp = exp_gain(fainted_pokemon_species, fainted_pokemon_level, your_level=pm.level, participants=participants, is_trainer=is_trainer, is_participant=is_part)
            
            # Store pre-level data for stat comparison
            pre_level = pm.level
            pre_exp = getattr(pm, 'exp', 0)
            pm_sid = _sid_for(pm.species)
            
            # Calculate pre-level stats
            try:
                base_stats = get_species(pm_sid)["base_stats"] if pm_sid else {}
                pre_stats = derive_stats(base_stats, pre_level) if base_stats else {}
            except Exception:
                pre_stats = {}
            
            # Apply XP and process any level-ups
            res = apply_experience(pm, gained_xp, species_id=pm_sid)
            
            # Display XP gain with screen clear
            from platinum.ui import typewriter as tw
            try:
                tw.clear_screen()
            except Exception:
                pass
            
            print(f"{pm.species.capitalize()} gained {gained_xp} EXP!")
            print("Press Enter to continue...")
            try:
                input()
            except Exception:
                pass
            
            # Handle level-ups with proper Pokemon sequence
            if res['leveled']:
                levels_gained = pm.level - pre_level
                _handle_multiple_level_ups(ctx, pm, pm_sid, pre_level, pre_stats, levels_gained, battle_session=session)
                    
    except Exception as e:
        print(f"[XP] Error applying experience on faint: {e}")


def _handle_multiple_level_ups(ctx, pokemon, species_id, start_level, pre_stats, levels_gained, *, battle_session=None):
    """Handle multiple level-ups from a single battle, showing proper Pokemon sequence."""
    import time
    from platinum.battle.factory import derive_stats
    from platinum.data.loader import get_species, level_up_learnset
    from platinum.ui.menu_nav import Menu, MenuItem
    from platinum.ui import typewriter as tw
    
    # Process each level individually for proper move learning
    current_level = start_level
    
    for level_num in range(levels_gained):
        current_level += 1
        
        # Calculate and show stat increases (level announcement is in the stat screen)
        try:
            base_stats = get_species(species_id)["base_stats"] if species_id else {}
            if base_stats:
                old_stats = derive_stats(base_stats, current_level - 1)
                new_stats = derive_stats(base_stats, current_level)
                _show_stat_increase_screen(pokemon, old_stats, new_stats, current_level, battle_session=battle_session)
        except Exception:
            pass
        
        # Check for new moves at this specific level
        _check_move_learning(ctx, pokemon, species_id, current_level)
        
        # 4. Check for evolution at this specific level
        _check_evolution(ctx, pokemon, species_id, current_level)
        
        # Small delay between levels if multiple
        if level_num < levels_gained - 1:
            try:
                time.sleep(0.5)
            except Exception:
                pass


def _show_stat_increase_screen(pokemon, old_stats, new_stats, new_level, *, battle_session=None):
    """Show the stat summary screen with stat increases."""
    from platinum.audio.player import audio
    from platinum.ui import typewriter as tw
    
    # Clear screen before displaying level-up screen
    try:
        tw.clear_screen()
    except Exception:
        pass
    
    # Initialize music path variable
    prev_music_path = None
    
    # Handle audio during level-up screen
    if battle_session:
        # Store current battle music path for later resume
        try:
            prev_music_path = getattr(audio, "_state").last_path
            # Stop battle music completely
            audio.stop_music()
        except Exception:
            pass
        
        # Play level-up sound as music (non-looping)
        try:
            audio.play_music("assets/audio/sfx/level_up.ogg", loop=False)
        except Exception:
            pass
    
    print(f"{pokemon.species.capitalize()} reached level {new_level}!")
    print("\nStats increased:")
    
    stat_names = {
        'hp': 'HP',
        'attack': 'Attack', 
        'defense': 'Defense',
        'sp_atk': 'Sp. Atk',
        'sp_def': 'Sp. Def',
        'speed': 'Speed'
    }
    
    for stat_key, stat_label in stat_names.items():
        old_val = old_stats.get(stat_key, 0)
        new_val = new_stats.get(stat_key, 0)
        increase = new_val - old_val
        
        if increase > 0:
            print(f"  {stat_label}: {old_val} → {new_val} (+{increase})")
    
    print("\nPress Enter to continue...")
    try:
        input()
    except Exception:
        pass
    
    # Clear screen after level-up screen
    try:
        tw.clear_screen()
    except Exception:
        pass
    
    # Check if battle is over before resuming music
    if battle_session:
        battle_over = battle_session.is_over()
        
        if not battle_over and prev_music_path:
            # Battle continues - resume battle music
            try:
                audio.play_music(prev_music_path, loop=True)
            except Exception:
                pass
        # If battle is over, don't resume music - let victory sequence handle it


def _check_move_learning(ctx, pokemon, species_id, level):
    """Check if Pokemon learns new moves at this level."""
    from platinum.data.loader import level_up_learnset
    from platinum.ui.menu_nav import Menu, MenuItem
    
    try:
        # Get moves learned at this specific level
        learnset = level_up_learnset(species_id) if species_id else []
        moves_at_level = [move for move in learnset if move.get('level') == level]
        
        if not moves_at_level:
            return
        
        # Ensure pokemon has moves list
        if not hasattr(pokemon, 'moves'):
            pokemon.moves = []
        elif pokemon.moves is None:
            pokemon.moves = []
        
        for move_data in moves_at_level:
            move_name = move_data.get('name', '').replace('-', ' ').title()
            
            print(f"{pokemon.species.capitalize()} wants to learn the move {move_name}.")
            
            # Check if Pokemon already knows 4 moves
            if len(pokemon.moves) >= 4:
                print(f"But {pokemon.species.capitalize()} can't learn more than four moves!")
                print(f"Delete a move to make room for {move_name}?")
                
                # Show move selection menu
                move_items = []
                for i, existing_move in enumerate(pokemon.moves):
                    display_name = existing_move.replace('-', ' ').title()
                    move_items.append(MenuItem(f"{i+1}. {display_name}", existing_move))
                move_items.append(MenuItem("Cancel", "cancel"))
                
                choice = Menu(
                    f"Which move should be forgotten?",
                    move_items,
                    allow_escape=True,
                    footer="↑/↓ W/S • Enter select • Esc cancel"
                ).run()
                
                if choice and choice != "cancel":
                    # Replace the chosen move
                    move_index = pokemon.moves.index(choice)
                    old_move = pokemon.moves[move_index].replace('-', ' ').title()
                    pokemon.moves[move_index] = move_data.get('name', '')
                    print(f"{pokemon.species.capitalize()} forgot {old_move} and learned {move_name}!")
                else:
                    print(f"{pokemon.species.capitalize()} did not learn {move_name}.")
            else:
                # Pokemon has room for the new move
                pokemon.moves.append(move_data.get('name', ''))
                print(f"{pokemon.species.capitalize()} learned {move_name}!")
                
    except Exception as e:
        print(f"[Move Learning] Error: {e}")


def _check_evolution(ctx, pokemon, species_id, level):
    """Check if Pokemon should evolve at this level."""
    from platinum.data.loader import get_species
    
    try:
        # Get evolution data for this species
        species_data = get_species(species_id) if species_id else {}
        evolution_chain = species_data.get('evolution_chain', {})
        
        if not evolution_chain:
            return
        
        # Check for level-based evolution
        evolves_to = evolution_chain.get('evolves_to', [])
        for evolution in evolves_to:
            evolution_trigger = evolution.get('evolution_details', [{}])[0]
            trigger = evolution_trigger.get('trigger', {})
            
            if trigger.get('name') == 'level-up':
                min_level = evolution_trigger.get('min_level')
                if min_level and level >= min_level:
                    evolved_species = evolution.get('species', {}).get('name', '').capitalize()
                    
                    print(f"What? {pokemon.species.capitalize()} is evolving!")
                    print("(Evolution system not yet implemented)")
                    print(f"{pokemon.species.capitalize()} would evolve into {evolved_species}!")
                    
                    # For now, just show the evolution message
                    # TODO: Implement full evolution sequence
                    break
                    
    except Exception as e:
        print(f"[Evolution] Error: {e}")


def _apply_shared_experience(ctx, session, trainer, *, is_trainer: bool = True):
    """Apply BDSP-style shared XP to all party members."""
    try:
        from platinum.battle.experience import exp_gain, apply_experience, growth_rate, required_exp_for_level
        from platinum.battle.factory import derive_stats
        from platinum.data.species_lookup import species_id
        from platinum.data.loader import get_species, possible_evolutions
        from platinum.ui.menu_nav import Menu, MenuItem  # Menu system
        from platinum.data.species_lookup import species_name as _species_name
        from platinum.ui import typewriter as tw
        
        # Get enemy data for XP calculation (use first enemy Pokemon)
        if not trainer.party:
            return
            
        enemy_pokemon = trainer.party[0]  # Use first Pokemon for XP calculation
        enemy_species = enemy_pokemon.species_id
        enemy_level = enemy_pokemon.level
        
        # Determine participants (active battlers)
        try:
            part_indices = set(getattr(session, 'player_participants', {session.player.active_index}))
        except Exception:
            part_indices = {session.player.active_index}
        participants = max(1, len(part_indices))
        
        def _sid_for(val):
            try:
                return species_id(val) if isinstance(val, str) else int(val)
            except Exception:
                return None
        
        def _animate_xp(member, gained_exp: int):
            """Animate XP gain for active Pokemon."""
            try:
                sid_local = _sid_for(member.species)
            except Exception:
                sid_local = None
            rate_name = growth_rate(sid_local) if sid_local is not None else 'Medium Fast'
            start_exp = getattr(member, 'exp', 0)
            start_level = member.level
            target_exp = start_exp + max(0, int(gained_exp))
            cur_exp = start_exp
            cur_level = start_level
            import time
            while cur_exp < target_exp and cur_level < 100:
                cur_req = required_exp_for_level(cur_level, rate=rate_name)
                next_req = required_exp_for_level(cur_level + 1, rate=rate_name) if cur_level < 100 else cur_req + 1
                step_to = min(target_exp, next_req)
                steps = max(1, (step_to - cur_exp) // 8)
                cur_exp = min(step_to, cur_exp + steps)
                print(f"{member.species.capitalize()} gaining EXP... {cur_exp - start_exp}/{gained_exp}")
                try:
                    time.sleep(0.02)
                except Exception:
                    pass
                if cur_exp >= next_req and cur_level < 100:
                    cur_level += 1
                    print(f"{member.species.capitalize()} leveled up to Lv{cur_level}!")
                    try:
                        time.sleep(0.05)
                    except Exception:
                        pass
            
            # Apply the actual experience
            before_level = member.level
            before_moves = list(getattr(member, 'moves', []) or [])
            before_sid = _sid_for(member.species)
            try:
                base_stats = get_species(before_sid)["base_stats"]
                stats_before = derive_stats(base_stats, before_level)
            except Exception:
                stats_before = {k: getattr(member, k, 0) for k in ("hp","attack","defense","sp_atk","sp_def","speed")}
            
            res_local = apply_experience(member, gained_exp, species_id=before_sid)
            after_level = member.level
            
            try:
                base_stats = get_species(before_sid)["base_stats"]
                stats_after = derive_stats(base_stats, after_level)
            except Exception:
                stats_after = stats_before
                
            if after_level > before_level:
                try:
                    tw.clear_screen()
                except Exception:
                    pass
                print(f"{member.species.capitalize()} grew to level {after_level}!")
                def _line(label: str, delta: int):
                    return f"{label} +{delta}" if delta > 0 else f"{label}"
                print(_line("HP", stats_after.get("hp",0) - stats_before.get("hp",0)))
                print(_line("Attack", stats_after.get("attack",0) - stats_before.get("attack",0)))
                print(_line("Defense", stats_after.get("defense",0) - stats_before.get("defense",0)))
                print(_line("Sp. Atk", stats_after.get("sp_atk",0) - stats_before.get("sp_atk",0)))
                print(_line("Sp. Def", stats_after.get("sp_def",0) - stats_before.get("sp_def",0)))
                print(_line("Speed", stats_after.get("speed",0) - stats_before.get("speed",0)))
                
                # Handle move learning
                learned_moves = list(res_local.get('learned') or [])
                if learned_moves:
                    moves_now = list(before_moves)
                    for nm in learned_moves:
                        if nm in moves_now:
                            continue
                        if len(moves_now) < 4:
                            print(f"{member.species.capitalize()} wants to learn {nm.replace('-', ' ').title()}.")
                            choice = Menu("Learn this move?", [MenuItem("Learn","yes"), MenuItem("Give up","no")], allow_escape=True).run()
                            if choice == "yes":
                                moves_now.append(nm)
                        else:
                            print(f"{member.species.capitalize()} wants to learn {nm.replace('-', ' ').title()}.")
                            items = [MenuItem(mv.replace('-', ' ').title(), value=mv) for mv in moves_now] + [MenuItem("Give up learning", value="__giveup__")]
                            sel = Menu("Replace which move?", items, allow_escape=True).run()
                            if sel and sel != "__giveup__":
                                try:
                                    i = moves_now.index(sel)
                                    moves_now[i] = nm
                                except Exception:
                                    pass
                    member.moves = moves_now[:4]
                
                # Handle evolution
                try:
                    possible = possible_evolutions(int(before_sid), level=member.level) if before_sid is not None else []
                except Exception:
                    possible = []
                if possible:
                    evo_id = possible[0]
                    print(f"Huh? {member.species.capitalize()} is evolving!")
                    evo_choice = Menu("Evolve now?", [MenuItem("Let it evolve","yes"), MenuItem("Stop evolution (B)","no")], allow_escape=True).run()
                    if evo_choice == "yes":
                        new_name = _species_name(evo_id).capitalize()
                        old_max = getattr(member, 'max_hp', 0)
                        try:
                            new_stats = derive_stats(get_species(evo_id)["base_stats"], member.level)
                        except Exception:
                            new_stats = None
                        member.species = new_name.lower()
                        if new_stats:
                            new_max = int(new_stats.get("hp", old_max or 0))
                            delta = max(0, new_max - int(old_max or 0))
                            member.max_hp = new_max
                            member.hp = min(member.max_hp, int(getattr(member, 'hp', 0)) + delta)
        
        # Calculate XP gains for all party members
        gains: list[int] = []
        for idx, pm in enumerate(ctx.state.party):
            is_part = idx in part_indices
            g = exp_gain(enemy_species, enemy_level, your_level=pm.level, participants=participants, is_trainer=is_trainer, is_participant=is_part)
            gains.append(g)
        
        # Apply XP to active Pokemon with animation
        active_idx = session.player.active_index
        if 0 <= active_idx < len(ctx.state.party):
            try:
                _animate_xp(ctx.state.party[active_idx], gains[active_idx])
            except Exception:
                try:
                    pm = ctx.state.party[active_idx]
                    sid0 = _sid_for(pm.species)
                    apply_experience(pm, gains[active_idx], species_id=sid0)
                except Exception:
                    pass
        
        # Apply XP to bench Pokemon (no animation)
        for idx, pm in enumerate(ctx.state.party):
            if idx == active_idx:
                continue
            pm_sid = _sid_for(pm.species)
            g = gains[idx]
            try:
                print(f"{pm.species.capitalize()} gained {g} EXP!")
            except Exception:
                pass
            res2 = apply_experience(pm, g, species_id=pm_sid)
            if res2['leveled']:
                print(f"{pm.species.capitalize()} grew to level {pm.level}!")
                if res2.get('learned'):
                    learned_str = ", ".join(m.title().replace('-', ' ') for m in res2['learned'])
                    print(f"Learned {learned_str}!")
                    
    except Exception as e:
        print(f"[XP] Error applying experience: {e}")


def run_trainer_battle(trainer_id: str, ctx, *, rng: Optional[random.Random] = None) -> str:
    """Run a battle using trainer JSON data."""
    from platinum.data.trainers import get_trainer
    from platinum.battle.factory import battler_from_species
    from platinum.data.species_lookup import species_id
    from platinum.battle.session import BattleSession, Party
    
    trainer = get_trainer(trainer_id)
    if not trainer:
        print(f"[battle] Trainer '{trainer_id}' not found")
        return "ERROR"
    
    if not ctx.state.party:
        print("[battle] Player has no party")
        return "ERROR"
    
    # Store previous music for later restoration
    previous_music = None
    try:
        previous_music = getattr(audio._state, 'last_path', None)
    except Exception:
        pass
    
    # Show approach dialogue
    print(f"{trainer.name}: {trainer.approach_dialogue}")
    
    # Set battle music if specified
    if trainer.music:
        try:
            audio.play_music(f"assets/audio/bgm/{trainer.music}.ogg", loop=True)
        except Exception:
            pass
    
    # Create trainer's party
    enemy_battlers = []
    for pokemon in trainer.party:
        # Check if this Pokemon requires a specific flag
        if pokemon.requires_flag and not ctx.has_flag(pokemon.requires_flag):
            continue
            
        try:
            battler = battler_from_species(pokemon.species_id, pokemon.level)
            enemy_battlers.append(battler)
        except Exception as e:
            print(f"[battle] Failed to create trainer pokemon {pokemon.species_id}: {e}")
            continue
    
    if not enemy_battlers:
        print("[battle] Trainer has no valid Pokemon")
        return "ERROR"
    
    # Create player's party
    player_battlers = []
    for pm in ctx.state.party:
        try:
            sid = species_id(pm.species)
            battler = battler_from_species(sid, pm.level)
            # Sync HP from save data
            if hasattr(battler, 'current_hp'):
                battler.current_hp = pm.hp
            player_battlers.append(battler)
        except Exception as e:
            print(f"[battle] Failed to create player pokemon {pm.species}: {e}")
            continue
    
    if not player_battlers:
        print("[battle] Player has no valid Pokemon")
        return "ERROR"
    
    # Run the battle with proper XP-on-faint sequence
    session = BattleSession(
        player=Party(player_battlers),
        enemy=Party(enemy_battlers),
        is_wild=False
    )
    
    # For now, use existing battle UI but apply per-faint XP after
    outcome = run_battle_ui(session, is_trainer=True, trainer_label=trainer.name, rng=rng)
    
    # Apply XP for any Pokemon that fainted during battle
    fainted_enemies = getattr(session, '_fainted_enemies', [])
    for enemy_species, enemy_level, was_trainer in fainted_enemies:
        _apply_exp_on_faint(ctx, session, enemy_species, enemy_level, is_trainer=was_trainer)
    
    # Handle post-battle sequence properly
    if outcome == "PLAYER_WIN":
        from platinum.ui import typewriter as tw
        
        # Clear screen and play victory music
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        # Play victory music after all XP is awarded
        victory_music = trainer.victory_music or "victory_trainer_battle"
        _play_victory_music(is_trainer=True, victory_music=victory_music)
        
        # Victory sequence with typewriter
        try:
            tw.type_out(f"You defeated {trainer.name}!")
        except Exception:
            print(f"You defeated {trainer.name}!")
        
        print("Press Enter to continue...")
        try:
            input()
        except Exception:
            pass
        
        # Clear screen for trainer dialogue
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        # Show trainer's loss dialogue with typewriter
        try:
            tw.type_out(f"{trainer.name}: {trainer.loss_dialogue}")
        except Exception:
            print(f"{trainer.name}: {trainer.loss_dialogue}")
        
        print("Press Enter to continue...")
        try:
            input()
        except Exception:
            pass
        
        # Clear screen for money award
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        # Award money
        if trainer.money_won > 0:
            try:
                tw.type_out(f"You earned ₽{trainer.money_won}!")
            except Exception:
                print(f"You earned ₽{trainer.money_won}!")
            
            if hasattr(ctx.state, 'money'):
                ctx.state.money += trainer.money_won
            
            print("Press Enter to continue...")
            try:
                input()
            except Exception:
                pass
        
        # Stop victory music after money screen
        try:
            audio.stop_music()
        except Exception:
            pass
        
        # Clear screen and resume previous music if available
        try:
            tw.clear_screen()
        except Exception:
            pass
        
        # Ensure victory music is fully stopped before resuming route music
        try:
            audio.stop_music()
        except Exception:
            pass
        
        # Resume previous music (usually route music)
        if previous_music and previous_music.endswith('.ogg'):
            try:
                # Add a small delay to ensure victory music has stopped
                import time
                time.sleep(0.1)
                # Stop any current music first to ensure clean transition
                audio.stop_music()
                time.sleep(0.1)
                # Start the route music
                audio.play_music(previous_music, loop=True)
                audio.set_music_volume(0.7)  # Set proper volume
            except Exception:
                pass
        else:
            # If no previous music info, just ensure all music is stopped
            try:
                audio.stop_music()
            except Exception:
                pass
        
        # Remove old shared XP system since we now do per-faint XP
        # _apply_shared_experience(ctx, session, trainer, is_trainer=True)
        
    elif outcome == "PLAYER_LOSS":
        print(f"{trainer.name}: {trainer.loss_dialogue}")
        if trainer.money_lost > 0:
            print(f"You lost ${trainer.money_lost}!")
            # Deduct money from player
            if hasattr(ctx.state, 'money'):
                ctx.state.money = max(0, ctx.state.money - trainer.money_lost)
    
    return outcome

__all__ = ["run_battle_ui", "run_trainer_battle"]
