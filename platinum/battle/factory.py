"""Factory helpers for constructing Battler instances from species data.

Shared across battle service, session tests, etc.
"""
from __future__ import annotations
from typing import Dict, List
from .core import Battler, Move
from .experience import clamp_level
from platinum.data.loader import get_species, level_up_learnset
from platinum.data.moves import get_move

def derive_stats(base: Dict[str,int], level: int) -> Dict[str,int]:
    stats = {}
    for k, v in base.items():
        if k == "hp":
            stats[k] = int(((2*v)*level)/100 + level + 10)
        else:
            stats[k] = int(((2*v)*level)/100 + 5)
    return stats

def battler_from_species(species_id: int, level: int, nickname: str | None = None) -> Battler:
    level = clamp_level(level)
    s = get_species(species_id)
    name = nickname or s["name"].capitalize()
    types = tuple(s["types"])  # type: ignore
    stats_calc = derive_stats(s["base_stats"], level)
    ability = s["abilities"]["primary"]
    lu = [m for m in level_up_learnset(species_id) if m["level"] <= level]
    lu_sorted = sorted(lu, key=lambda x: (x["level"], x["name"]))
    chosen = lu_sorted[-4:]
    moves: List[Move] = []
    for mv in chosen:
        raw_name = mv["name"]
        md = get_move(raw_name)
        _dr = md.get("drain")
        drain_ratio = tuple(_dr) if isinstance(_dr, (list, tuple)) else None
        _rr = md.get("recoil")
        recoil_ratio = tuple(_rr) if isinstance(_rr, (list, tuple)) else None
        _mh = md.get("multi_hit")
        hits = tuple(_mh) if isinstance(_mh, (list, tuple)) else None
        multi_turn = md.get("multi_turn")
        if multi_turn is not None and not isinstance(multi_turn, (list, tuple)):
            multi_turn = None
        moves.append(Move(
            name=md["display_name"],
            type=md.get("type") or types[0],
            category=md.get("category") or "status",
            power=md.get("power") or 0,
            accuracy=md.get("accuracy"),
            priority=md.get("priority", 0),
            crit_rate_stage=md.get("crit_rate_stage", 0),
            hits=hits, drain_ratio=drain_ratio, recoil_ratio=recoil_ratio,
            flinch_chance=md.get("flinch_chance", 0),
            ailment=md.get("ailment"),
            ailment_chance=md.get("ailment_chance", 0),
            stat_changes=[{ "stat": sc.get("stat"), "change": sc.get("change"), "chance": sc.get("chance",0)} for sc in md.get("stat_changes", [])],
            target=md.get("targets") or "selected-pokemon",
            flags={"internal": raw_name} | (md.get("flags", {}) or {}),
            multi_turn=tuple(multi_turn) if multi_turn else None,
            max_pp=md.get("pp", 0) or 0,
            pp=md.get("pp", 0) or 0
        ))
    return Battler(species_id=species_id, name=name, level=level, types=types, stats={
        "hp": stats_calc["hp"],
        "atk": stats_calc["attack"],
        "def": stats_calc["defense"],
        "sp_atk": stats_calc["sp_atk"],
        "sp_def": stats_calc["sp_def"],
        "speed": stats_calc["speed"],
    }, ability=ability, moves=moves)

__all__ = ["battler_from_species","derive_stats"]
