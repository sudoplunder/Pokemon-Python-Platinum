"""Level cap & obedience (disobedience) helpers.

Implements simple badge-based level cap and a probability that a Pokémon
above the cap will disobey and waste its turn.

Mapping (inclusive caps):
  0 badges -> 20 (assumed; spec started at 1 badge so we pick a conservative pre-badge cap)
  1 badge  -> 25
  2 badges -> 30
  3 badges -> 35
  4 badges -> 40
  5 badges -> 45
  6 badges -> 50
  7 badges -> 55
  8 badges -> 100 

Disobedience chance scales 10% per level above the cap, clamped at 50%.
This is a simplification of the mainline formula.
"""
from __future__ import annotations

BADGE_LEVEL_CAPS = {
    0: 20,
    1: 25,
    2: 30,
    3: 35,
    4: 40,
    5: 45,
    6: 50,
    7: 55,
    8: 999,  # effectively unlimited
}


def level_cap_for_badges(badge_count: int) -> int:
    if badge_count >= 8:
        return BADGE_LEVEL_CAPS[8]
    if badge_count < 0:
        badge_count = 0
    return BADGE_LEVEL_CAPS.get(badge_count, 55)


def disobedience_chance(level: int, cap: int) -> float:
    over = level - cap
    if over <= 0:
        return 0.0
    # 10% per level over, capped at 50%
    return min(0.1 * over, 0.5)

__all__ = ["level_cap_for_badges", "disobedience_chance"]
