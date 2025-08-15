from __future__ import annotations
import random
from platinum.battle.models import Pokemon, Move

TYPE_EFFECTIVENESS = {
    ("fire","grass"): 2.0,
    ("water","fire"): 2.0,
    ("grass","water"): 2.0,
    ("electric","water"): 2.0,
    ("grass","fire"): 0.5,
    ("fire","water"): 0.5,
    ("water","grass"): 0.5,
    ("normal","rock"): 0.5,
    ("fire","rock"): 0.5,
    ("fire","rock"): 0.5,
    ("water","rock"): 2.0,
    ("grass","rock"): 2.0,
}

def effectiveness(move_type: str, defender: Pokemon) -> float:
    mult = 1.0
    for t in defender.types:
        mult *= TYPE_EFFECTIVENESS.get((move_type, t), 1.0)
    return mult

def accuracy_check(move: Move, rng: random.Random) -> bool:
    if move.accuracy == 0:  # status moves with guaranteed hit
        return True
    return rng.randint(1,100) <= move.accuracy

def is_critical(rng: random.Random) -> bool:
    return rng.randint(1,16) == 1

def calculate_damage(attacker: Pokemon, defender: Pokemon, move: Move, rng: random.Random) -> tuple[int, dict]:
    if move.power <= 0:
        return 0, {"crit": False, "stab": 1.0, "type": 1.0}
    atk_stat = attacker.stats.atk if move.category == "physical" else attacker.stats.spa
    def_stat = defender.stats.def_ if move.category == "physical" else defender.stats.spd
    base = (((2*attacker.level)/5)+2)
    base = (base * move.power * atk_stat / max(1, def_stat)) / 50 + 2
    crit = is_critical(rng)
    if crit:
        base *= 2
    stab = 1.5 if move.type in attacker.types else 1.0
    type_mult = effectiveness(move.type, defender)
    rand = rng.uniform(0.85, 1.0)
    dmg = int(base * stab * type_mult * rand)
    dmg = max(1, dmg)
    return dmg, {"crit": crit, "stab": stab, "type": type_mult}