"""Smoke validator for move JSONs.

Runs each move once (or twice for charge moves) in a simple 1v1 and reports
whether something observable happened (damage, status, stat stage, field effect),
or the engine emitted an acceptable no-effect message.

Outputs a concise console summary and a JSON report under scripts/reports/.
"""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import random

from platinum.battle.core import BattleCore, Move
from platinum.battle.session import BattleSession, Party
from platinum.battle.factory import battler_from_species
from platinum.data.moves import all_moves

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "scripts" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "move_smoke_report.json"


def build_move_from_json(md: Dict[str, Any]) -> Move:
    # Normalize list/tuple fields
    _dr = md.get("drain")
    drain = tuple(_dr) if isinstance(_dr, (list, tuple)) else None
    _rr = md.get("recoil")
    recoil = tuple(_rr) if isinstance(_rr, (list, tuple)) else None
    _mh = md.get("multi_hit")
    hits = tuple(_mh) if isinstance(_mh, (list, tuple)) else None
    _mt = md.get("multi_turn")
    multi_turn = tuple(_mt) if isinstance(_mt, (list, tuple)) else None
    flags = dict(md.get("flags") or {})
    # Force high probabilities for smoke to reduce RNG flakiness
    ailment = md.get("ailment")
    ailment_chance = md.get("ailment_chance") or 0
    if ailment and ailment not in {"none","unknown"} and ailment_chance < 100:
        ailment_chance = 100
    stat_changes = []
    for sc in (md.get("stat_changes") or []):
        stat_changes.append({
            "stat": sc.get("stat"),
            "change": sc.get("change", 0),
            "chance": sc.get("chance", 0) or 100
        })
    # Moves with null power in data become 0 in engine
    power = md.get("power") or 0
    accuracy = md.get("accuracy")
    if accuracy is not None and accuracy < 100:
        accuracy = 100
    pp = md.get("pp") or 5
    return Move(
        name=md.get("display_name") or md["name"].replace("-"," ").title(),
        type=md.get("type") or "normal",
        category=md.get("category") or "status",
        power=power,
        accuracy=accuracy,
        priority=md.get("priority", 0),
        crit_rate_stage=md.get("crit_rate_stage", 0),
        hits=hits,
        drain_ratio=drain,
        recoil_ratio=recoil,
        flinch_chance=md.get("flinch_chance", 0) or 0,
        ailment=ailment,
        ailment_chance=ailment_chance,
        stat_changes=stat_changes,
        target=md.get("targets") or "selected-pokemon",
        flags=flags,
        multi_turn=multi_turn,
        max_pp=pp,
        pp=pp,
    )


def simulate_move(slug: str, md: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    rng = random.Random(123)
    core = BattleCore(rng=rng)
    # Choose targets to avoid immunities for the move type
    move_type = (md.get("type") or "normal").lower()
    attacker_id = 399  # Bidoof (Normal)
    # Default neutral target is Bidoof
    target_id = 399
    type_target_map = {
        "ghost": 92,        # Gastly (not immune to Ghost)
        "electric": 396,    # Starly (Flying weak to Electric)
        "ground": 74,       # Geodude (weak to Ground)
        "poison": 387,      # Turtwig (Grass weak to Poison)
        "rock": 396,        # Starly (Flying weak to Rock)
        "fire": 387,        # Turtwig (Grass weak to Fire)
        "water": 74,        # Geodude (Rock/Ground weak to Water)
        "grass": 74,        # Geodude (weak to Grass)
        "ice": 396,         # Starly (Flying weak to Ice)
        "fighting": 399,    # Bidoof (Normal weak to Fighting)
        "dragon": 399,      # Neutral
        "dark": 399,        # Neutral
        "steel": 399,       # Neutral
        "bug": 399,         # Neutral
        "flying": 399,      # Neutral
        "psychic": 399,     # Neutral
        "normal": 399,      # Neutral
    }
    target_id = type_target_map.get(move_type, 399)
    player_b = battler_from_species(attacker_id, 50)
    enemy_b = battler_from_species(target_id, 50)
    # Disambiguate logs in case species share names in some forms
    player_b.name = f"Player {player_b.name}"
    enemy_b.name = f"Enemy {enemy_b.name}"
    # Player move under test; enemy uses Splash (no-op)
    test_move = build_move_from_json(md)
    player_b.moves = [test_move]
    enemy_b.moves = [Move(name="Splash", type="normal", category="status", accuracy=None)]
    session = BattleSession(Party([player_b]), Party([enemy_b]), core=core)

    # snapshot before
    e_before_hp = session.enemy.active().current_hp or session.enemy.active().stats["hp"]
    p_before_hp = session.player.active().current_hp or session.player.active().stats["hp"]
    stages_before = asdict(session.enemy.active().stages)
    p_stages_before = asdict(session.player.active().stages)
    status_before = (session.enemy.active().status, session.player.active().status)

    # Steps: handle charge moves with 2 steps
    steps = 2 if test_move.flags.get("charge") else 1
    for _ in range(steps):
        session.step(player_move_idx=0, enemy_move_idx=0)

    # Build logs and split into player's vs enemy's action segments to avoid
    # attributing the enemy's Splash message ("But nothing happened.") to the player's move.
    full_lines = list(session.log)
    log = "\n".join(full_lines).lower()
    enemy_name = session.enemy.active().name.lower()
    player_name = session.player.active().name.lower()
    enemy_used_idx = None
    player_used_idx = None
    for i, ln in enumerate(full_lines):
        low = ln.lower()
        if enemy_used_idx is None and low.startswith(f"{enemy_name} used "):
            enemy_used_idx = i
        if player_used_idx is None and low.startswith(f"{player_name} used "):
            player_used_idx = i
        if enemy_used_idx is not None and player_used_idx is not None:
            break
    if player_used_idx is None:
        # Fallback to everything before enemy action
        player_lines = full_lines if enemy_used_idx is None else full_lines[:enemy_used_idx]
    else:
        # Take from player's action to before the opponent's action if it comes after
        if enemy_used_idx is not None and enemy_used_idx > player_used_idx:
            player_lines = full_lines[player_used_idx:enemy_used_idx]
        else:
            player_lines = full_lines[player_used_idx:]
    player_log = "\n".join(player_lines).lower()
    e_after_hp = session.enemy.active().current_hp or session.enemy.active().stats["hp"]
    p_after_hp = session.player.active().current_hp or session.player.active().stats["hp"]
    stages_after = asdict(session.enemy.active().stages)
    p_stages_after = asdict(session.player.active().stages)
    status_after = (session.enemy.active().status, session.player.active().status)

    # Determine observed effects
    damage_dealt = int(e_after_hp) < int(e_before_hp)
    user_healed_or_damaged = int(p_after_hp) != int(p_before_hp)
    stage_changed = stages_before != stages_after or p_stages_before != p_stages_after
    status_changed = status_before != status_after
    field_changed = any(
        key in player_log for key in [
            "sunlight", "rain", "sandstorm", "hail", "reflect", "light screen", "wore off", "started", "kicked up",
            "veil of water", "aqua ring", "ability was suppressed", "mist shrouded", "levitated",
            "dimensions were twisted", "the dimensions were twisted", "pointed stones", "stat changes were eliminated"
        ]
    )
    no_effect_msg = "doesn't affect" in player_log
    nothing_happened_msg = "nothing happened" in player_log
    failed_msg = "but it failed" in player_log
    began_charge = "began charging" in log
    unleashed = "unleashes" in log
    faint_in_log = "fainted!" in log
    impact_msg = (" used " in player_log) and ("super effective" in player_log or "not very effective" in player_log or "critical hit" in player_log)

    category = md.get("category") or "status"
    power = md.get("power") or 0
    is_status = category == "status"

    success = False
    reasons: List[str] = []
    if test_move.flags.get("charge"):
        if began_charge and unleashed:
            success = True
        else:
            reasons.append("charge flow messages missing")
    elif not is_status and power > 0:
        if damage_dealt or no_effect_msg or faint_in_log or impact_msg:
            success = True
        else:
            reasons.append("no damage and no 'doesn\'t affect' message")
    else:
        # Treat any actual damage (even if power==0 in data) as success (e.g., Dragon Rage, Seismic Toss)
        if damage_dealt or stage_changed or status_changed or field_changed or no_effect_msg or nothing_happened_msg or user_healed_or_damaged or failed_msg or faint_in_log or impact_msg:
            success = True
        else:
            reasons.append("no observable effect or expected message")

    return success, {
        "slug": slug,
        "name": md.get("display_name"),
        "category": category,
        "type": md.get("type"),
        "power": power,
        "flags": md.get("flags", {}),
        "damage_dealt": damage_dealt,
        "user_hp_changed": user_healed_or_damaged,
        "stage_changed": stage_changed,
        "status_changed": status_changed,
        "field_changed": field_changed,
        "no_effect_msg": no_effect_msg,
        "nothing_happened_msg": nothing_happened_msg,
    "faint_in_log": faint_in_log,
    "impact_msg": impact_msg,
        "began_charge": began_charge,
        "unleashed": unleashed,
        "log_tail": "\n".join(session.log[-5:]),
        "success": success,
        "reasons": reasons,
    }


def main():
    moves = all_moves()
    results: List[Dict[str, Any]] = []
    ok = 0
    fail = 0
    for slug, md in moves.items():
        try:
            success, info = simulate_move(slug, md)
        except Exception as ex:
            success = False
            info = {"slug": slug, "name": md.get("display_name"), "error": str(ex), "success": False, "reasons": ["exception"]}
        results.append(info)
        if success:
            ok += 1
        else:
            fail += 1
    REPORT_PATH.write_text(json.dumps({
        "total": len(results),
        "ok": ok,
        "fail": fail,
        "results": results,
    }, indent=2))
    print(f"Move smoke complete: {ok}/{len(results)} OK, {fail} need review. Report: {REPORT_PATH}")
    # Print the first few failures for quick view
    for r in results:
        if not r.get("success"):
            print(f"- {r['slug']}: {', '.join(r.get('reasons', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
