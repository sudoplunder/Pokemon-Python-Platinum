"""Experience calculation, growth rates, level-up handling & move learning.

Implements BDSP-style:
- EXP Share always on: all party members gain EXP; participants get full share; bench gets reduced.
- EXP gained on captures as well as KOs.
- Growth curves loaded from BDSP_EXP_Table.csv for six groups.
"""
from __future__ import annotations
from typing import Iterable, Dict, List, Optional
from pathlib import Path
from platinum.data.loader import get_species, level_up_learnset
MIN_LEVEL = 1
MAX_LEVEL = 100

# ---------------- BDSP EXP Table (loaded once) -----------------
_EXP_TABLE: Dict[str, List[int]] | None = None

def _load_exp_table() -> Dict[str, List[int]]:
    global _EXP_TABLE
    if _EXP_TABLE is not None:
        return _EXP_TABLE
    # Initialize defaults in case file missing
    columns = ["Erratic","Fast","Medium Fast","Medium Slow","Slow","Fluctuating"]
    table: Dict[str, List[int]] = {col: [0]*(MAX_LEVEL+1) for col in columns}
    try:
        fp = Path(__file__).with_name("BDSP_EXP_Table.csv")
        lines = fp.read_text().splitlines()
        if not lines:
            _EXP_TABLE = table
            return table
        header = [h.strip() for h in lines[0].split(",")]
        col_idx = {name: header.index(name) for name in columns if name in header}
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if not parts or not parts[0].isdigit():
                continue
            lvl = int(parts[0])
            if lvl < 1 or lvl > MAX_LEVEL:
                continue
            for name, idx in col_idx.items():
                try:
                    val = int(parts[idx])
                except Exception:
                    val = 0
                if val < 0:
                    val = 0
                table[name][lvl] = val
    except Exception:
        # Leave defaults (zeros); we'll fall back to cubic if needed
        pass
    _EXP_TABLE = table
    return table

def clamp_level(level: int) -> int:
    try:
        return max(MIN_LEVEL, min(int(level), MAX_LEVEL))
    except Exception:
        return MIN_LEVEL

GROWTH_RATE_DEFAULT = "Medium Fast"

def base_experience(species_id: int) -> int:
    try:
        sp = get_species(species_id)
        for key in ("base_experience","base_exp","exp_yield"):
            if key in sp:
                return int(sp[key])
    except Exception:
        pass
    return 64  # fallback average


def growth_rate(species_id: int) -> str:
    try:
        sp = get_species(species_id)
        raw = (sp.get("growth_rate") or GROWTH_RATE_DEFAULT)
    except Exception:
        raw = GROWTH_RATE_DEFAULT
    r = str(raw).lower().replace("_","-")
    mapping = {
        "erratic": "Erratic",
        "fast": "Fast",
        "medium-fast": "Medium Fast",
        "medium": "Medium Fast",
        "medium-slow": "Medium Slow",
        "slow": "Slow",
        "fluctuating": "Fluctuating",
    }
    return mapping.get(r, GROWTH_RATE_DEFAULT)


def required_exp_for_level(level: int, *, rate: str | None = None) -> int:
    """Total EXP required to be at given level per growth group.

    Uses BDSP_EXP_Table.csv when available; clamps negatives and L<=1 to 0.
    """
    if level <= 1:
        return 0
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    r = rate or GROWTH_RATE_DEFAULT
    tbl = _load_exp_table()
    if r in tbl and tbl[r][level] > 0:
        return tbl[r][level]
    # Fallback cubic approximations if table missing
    lvl3 = level ** 3
    if r == "Fast":
        return int(0.8 * lvl3)
    if r == "Slow":
        return int(1.25 * lvl3)
    if r == "Medium Slow":
        return max(0, int((6/5)*lvl3 - 15*(level**2) + 100*level - 140))
    return lvl3  # Medium Fast default


def exp_gain(
    enemy_species: int,
    enemy_level: int,
    *,
    your_level: int | None = None,
    participants: int = 1,
    is_trainer: bool = False,
    is_participant: bool = True,
    traded: bool = False,
    lucky_egg: bool = False,
    other_mod: float = 1.0,
) -> int:
    """BDSP-like EXP formula with EXP Share.

    EXP = floor( a * b * L / (7 * s) ) * t * e * v * f
      a = base EXP yield of defeated species
      b = defeated Pokémon level
      L = level factor = (2*OppLvl + 10) / (YourLvl + OppLvl + 10)
      s = number of participants (those who battled)
      t = 1.5 if traded else 1
      e = 1.5 if lucky egg else 1
      v = 1.5 if trainer pokemon else 1
      f = other modifiers
    Bench recipients (EXP Share) get ~50% of participant result.
    """
    a = base_experience(enemy_species)
    b = max(1, int(enemy_level))
    yl = int(your_level) if your_level is not None else b
    # Level scaling factor
    L = (2 * b + 10) / (yl + b + 10)
    s = max(1, int(participants or 1))
    base = int((a * b * L) / (7 * s))
    # Multipliers
    t = 1.5 if traded else 1.0
    e = 1.5 if lucky_egg else 1.0
    v = 1.5 if is_trainer else 1.0
    f = float(other_mod or 1.0)
    total = int(base * t * e * v * f)
    if not is_participant:
        total = int(total * 0.5)  # bench reduced share
    return max(total, 1)


def _learnset_moves_for_level(species_id: int, level: int) -> list[str]:
    try:
        entries = level_up_learnset(species_id)
        names = [e["name"] for e in entries if int(e.get("level", 0)) <= level]
        return sorted(set(names), key=lambda n: names.index(n))  # preserve first occurrence order
    except Exception:
        return []


def learn_new_moves(member, species_id: int) -> list[str]:
    """Return list of newly learned move internal names after reaching current level.

    Mutates member.moves (list[str]) enforcing max size 4 (forget oldest).
    """
    if not hasattr(member, 'moves'):
        return []
    have = list(getattr(member, 'moves', []) or [])
    should_have = _learnset_moves_for_level(species_id, member.level)
    new_moves: list[str] = []
    for mv in should_have:
        if mv not in have:
            have.append(mv)
            new_moves.append(mv)
            if len(have) > 4:
                # forget oldest (index 0)
                have.pop(0)
    member.moves = have
    return new_moves


def apply_experience(member, gained: int, *, species_id: int | None = None) -> dict:
    """Apply XP to a PartyMember-like object (with species, level, exp fields).

    Returns dict including any learned moves.
    """
    before_level = member.level
    member.exp = getattr(member, 'exp', 0) + gained
    leveled = False
    rate = growth_rate(species_id) if species_id is not None else GROWTH_RATE_DEFAULT
    # Enforce cap: do not exceed MAX_LEVEL
    while member.level < MAX_LEVEL and member.exp >= required_exp_for_level(member.level + 1, rate=rate):
        member.level += 1
        leveled = True
    # Clamp level defensively
    member.level = clamp_level(member.level)
    learned: list[str] = []
    if leveled and species_id is not None:
        learned = learn_new_moves(member, species_id)
    return {"gained": gained, "leveled": leveled, "from": before_level, "to": member.level, "learned": learned}

__all__ = [
    "exp_gain","apply_experience","required_exp_for_level","growth_rate","learn_new_moves","clamp_level","MIN_LEVEL","MAX_LEVEL"
]
