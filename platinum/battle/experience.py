"""Experience calculation, growth rates, level-up handling & move learning.

Growth rate groups (simplified approximations of Gen IV):
  fast, medium, slow. (We can extend later: erratic, fluctuating, medium-slow.)
Formula placeholder mapping implemented in `required_exp_for_level`.
"""
from __future__ import annotations
from typing import Iterable
from platinum.data.loader import get_species, level_up_learnset
MIN_LEVEL = 1
MAX_LEVEL = 100

def clamp_level(level: int) -> int:
    try:
        return max(MIN_LEVEL, min(int(level), MAX_LEVEL))
    except Exception:
        return MIN_LEVEL

GROWTH_RATE_DEFAULT = "medium"

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
        return sp.get("growth_rate", GROWTH_RATE_DEFAULT)
    except Exception:
        return GROWTH_RATE_DEFAULT


def required_exp_for_level(level: int, *, rate: str | None = None) -> int:
    # Approx curves (not exact canon):
    # fast: 0.8 * n^3, medium: n^3, slow: 1.25 * n^3
    if level <= 1:
        return 0
    if level > MAX_LEVEL:
        level = MAX_LEVEL
    r = (rate or GROWTH_RATE_DEFAULT).lower()
    base = level ** 3
    if r == "fast":
        return int(0.8 * base)
    if r == "slow":
        return int(1.25 * base)
    return base


def exp_gain(enemy_species: int, enemy_level: int, *, is_trainer: bool) -> int:
    b = base_experience(enemy_species)
    gain = int((b * enemy_level) / 7)
    if is_trainer:
        gain = int(gain * 1.5)
    return max(gain, 1)


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
