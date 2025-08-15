from __future__ import annotations
from platinum.battle.models import Pokemon, Move
from platinum.battle.mechanics import effectiveness

def choose_move(user: Pokemon, foe: Pokemon):
    best = None
    best_score = -1
    for m in user.moves:
        power = m.power if m.power > 0 else 0
        eff = effectiveness(m.type, foe)
        score = power * eff
        if score > best_score:
            best_score = score
            best = m
    return best or user.moves[0]