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
from platinum.battle.session import BattleSession, Party
from platinum.battle.core import Move, Battler
from platinum.core.types import format_types

try:
    from colorama import Fore, Style
except Exception:  # pragma: no cover
    class _F: GREEN = RED = CYAN = YELLOW = MAGENTA = WHITE = RESET = ""
    class _S: RESET_ALL = ""
    Fore = _F(); Style = _S()


def _hp_bar(cur: int, max_hp: int, width: int = 20) -> str:
    cur = max(0, min(cur, max_hp))
    filled = int((cur / max_hp) * width) if max_hp else 0
    if max_hp == 0: filled = 0
    if filled == width and cur < max_hp:  # rounding edge-case
        filled -= 1
    # Color thresholds
    ratio = cur / max_hp if max_hp else 0
    if ratio >= 0.5:
        col = getattr(Fore, 'GREEN', '')
    elif ratio >= 0.25:
        col = getattr(Fore, 'YELLOW', '')
    else:
        col = getattr(Fore, 'RED', '')
    return f"{col}[{'#'*filled}{'-'*(width-filled)}]{Style.RESET_ALL} {cur}/{max_hp}"


def _print_state(session: BattleSession):
    p = session.player.active()
    e = session.enemy.active()
    p_types = format_types(p.types)
    e_types = format_types(e.types)
    print()
    print(f"Your {p.name} [{p_types}] Lv{p.level}  {_hp_bar(p.current_hp or 0, p.stats['hp'])}")
    print(f"Foe  {e.name} [{e_types}] Lv{e.level}  {_hp_bar(e.current_hp or 0, e.stats['hp'])}")


def _enemy_move_index(e: Battler, rng: random.Random) -> int:
    usable = [i for i, m in enumerate(e.moves) if m.max_pp == 0 or m.pp > 0]
    if not usable:
        return 0
    return rng.choice(usable)


_TYPE_COLORS = {
    'normal': Fore.WHITE,
    'fire': Fore.RED,
    'water': Fore.CYAN,
    'grass': Fore.GREEN,
    'electric': Fore.YELLOW,
    'ice': Fore.CYAN,
    'fighting': Fore.MAGENTA,
    'poison': Fore.MAGENTA,
    'ground': Fore.YELLOW,
    'flying': Fore.WHITE,
    'psychic': Fore.MAGENTA,
    'bug': Fore.GREEN,
    'rock': Fore.YELLOW,
    'ghost': Fore.MAGENTA,
    'dragon': Fore.CYAN,
    'dark': Fore.WHITE,
    'steel': Fore.WHITE,
}

def _choose_move(p: Battler) -> int | None:
    items: List[MenuItem] = []
    if not p.moves:
        return 0
    for i, mv in enumerate(p.moves):
        pp_txt = f"{mv.pp}/{mv.max_pp}" if mv.max_pp else "--"
        disabled = (mv.max_pp > 0 and mv.pp <= 0)
        col = _TYPE_COLORS.get(mv.type, '')
        items.append(MenuItem(label=f"{col}{mv.name}{Style.RESET_ALL} ({pp_txt})", value=str(i), disabled=disabled, help_text=mv.type))
    m = Menu("Fight", items, allow_escape=True, footer="↑/↓ W/S • Enter use • Esc back")
    res = m.run()
    if res is None:
        return None
    return int(res)


def run_battle_ui(session: BattleSession, *, is_trainer: bool = False, rng: Optional[random.Random] = None, inventory: Optional[Dict[str,int]] = None) -> str:
    rng = rng or random.Random()
    from platinum.system.settings import Settings
    if getattr(Settings.load().data, 'debug', False):
        print(f"[battle] Starting {'trainer' if is_trainer else 'wild'} battle!")
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
    while not session.is_over():
        _print_state(session)
        main_items = [
            MenuItem("Fight", "fight"),
            MenuItem("Pokemon", "pokemon"),
            MenuItem("Bag", "bag"),
            MenuItem("Run", "run", disabled=is_trainer),
        ]
        choice = Menu("Choose an action", main_items, allow_escape=False, footer="↑/↓ W/S • Enter select" ).run()
        if choice == "fight":
            mv_idx = _choose_move(session.player.active())
            if mv_idx is None:
                continue  # back out
            enemy_idx = _enemy_move_index(session.enemy.active(), rng)
            pre_turn_log_len = len(session.log)
            session.step(player_move_idx=mv_idx, enemy_move_idx=enemy_idx)
            new_msgs = session.log[pre_turn_log_len:]
            for msg in new_msgs:
                print(msg)
        elif choice == "pokemon":
            party_items: List[MenuItem] = []
            for i, b in enumerate(session.player.members):
                hp_bar = _hp_bar(b.current_hp or 0, b.stats['hp'])
                disabled = (b.current_hp or 0) <= 0 or i == session.player.active_index
                party_items.append(MenuItem(label=f"{b.name} Lv{b.level} {hp_bar}", value=str(i), disabled=disabled))
            m = Menu("Switch Pokémon", party_items, allow_escape=True, footer="Enter to switch • Esc cancel")
            sel = m.run()
            if sel is not None:
                session.player.active_index = int(sel)
                print(f"Go! {session.player.active().name}!")
        elif choice == "bag":
            inv = inventory or {}
            usable_entries: List[MenuItem] = []
            for name, count in sorted(inv.items()):
                if count < 1:
                    continue
                label = f"{name.replace('-', ' ').title()} x{count}"
                usable_entries.append(MenuItem(label, value=name))
            if not usable_entries:
                print("(Bag is empty)")
                continue
            sel = Menu("Bag", usable_entries, allow_escape=True, footer="Enter use • Esc back").run()
            if sel is None:
                continue
            if sel in {"potion"}:
                target = session.player.active()
                if (target.current_hp or 0) >= target.stats['hp']:
                    print("It won't have any effect.")
                else:
                    heal = min(20, target.stats['hp'] - (target.current_hp or 0))
                    target.current_hp = (target.current_hp or 0) + heal
                    inv[sel] -= 1
                    print(f"Restored {heal} HP!")
            elif sel.endswith("ball"):
                if session.is_wild:
                    result = session.attempt_capture(ball=sel)
                    inv[sel] -= 1
                    if result == 'CAPTURED':
                        print("Gotcha! Pokémon captured!")
                        return 'PLAYER_WIN'
                    else:
                        print(result.replace('_', ' ').title())
                        enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                        session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
                else:
                    print("You can't use that here.")
            else:
                print("Nothing happened.")
        elif choice == "run":
            if is_trainer:
                print("You can't run from a trainer battle!")
            else:
                if session.attempt_flee():
                    print("Got away safely!")
                    return "ESCAPE"
                else:
                    print("Couldn't escape!")
                    enemy_idx = _enemy_move_index(session.enemy.active(), rng)
                    session.step(player_move_idx=0, enemy_move_idx=enemy_idx)
        else:
            continue
    outcome = session.outcome()
    if getattr(Settings.load().data, 'debug', False):
        print(f"[battle] Battle ended: {outcome}")
    return outcome

__all__ = ["run_battle_ui"]
