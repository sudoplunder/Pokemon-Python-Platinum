"""Capture & flee mechanics (simplified Gen IV formula variants)."""
from __future__ import annotations
from dataclasses import dataclass
import random
from typing import Optional

# Ball modifiers (subset)
BALL_MODIFIERS = {
    'poke-ball': 1.0,
    'great-ball': 1.5,
    'ultra-ball': 2.0,
    'dusk-ball': 3.5,  # ignoring time/area gating for now
    'quick-ball': 4.0, # only turn 1 (not enforced here yet)
    'master-ball': float('inf'),
}

STATUS_BONUS = {
    'slp': 2.0,
    'frz': 2.0,
    'par': 1.5,
    'brn': 1.5,
    'psn': 1.5,
    'tox': 1.5,
}

@dataclass
class CaptureResult:
    success: bool
    shakes: int
    critical: bool = False


def capture_chance(capture_rate: int, max_hp: int, current_hp: int, ball: str, status: str) -> float:
    if BALL_MODIFIERS.get(ball,1.0) == float('inf'):
        return 1.0
    ball_mod = BALL_MODIFIERS.get(ball, 1.0)
    status_mod = STATUS_BONUS.get(status, 1.0)
    # Gen IV like formula (simplified):
    # a = (((3*maxHP - 2*currentHP) * capture_rate * ball_mod) / (3*maxHP)) * status_mod
    a = (((3*max_hp - 2*current_hp) * capture_rate * ball_mod) / (3*max_hp)) * status_mod
    # Cap a at 255
    if a > 255: a = 255
    return a / 255.0


def attempt_capture(rng: random.Random, capture_rate: int, max_hp: int, current_hp: int, ball: str, status: str) -> CaptureResult:
    if BALL_MODIFIERS.get(ball,1.0) == float('inf'):
        return CaptureResult(True, 3, critical=True)
    chance = capture_chance(capture_rate, max_hp, current_hp, ball, status)
    # emulate shakes (simplified probability; not the exact shake check formula)
    shakes = 0
    for _ in range(3):
        if rng.random() <= chance:
            shakes += 1
        else:
            break
    return CaptureResult(shakes == 3, shakes)


def flee_success(rng: random.Random, player_speed: int, enemy_speed: int, attempts: int) -> bool:
    """Return True if flee succeeds.

    Adjusted to be more forgiving for early prototype: scales faster with attempts
    and guarantees success by attempt 3 when player is faster.
    """
    if enemy_speed <= 0:
        return True
    # Base ratio term (cap at 255 early)
    ratio_term = (player_speed * 140) // max(1, enemy_speed)  # slightly higher than 128 baseline
    attempt_bonus = 60 * (attempts - 1)  # grows 0,60,120,...
    f_val = ratio_term + attempt_bonus + 20  # flat offset for baseline chance
    if player_speed > enemy_speed and attempts >= 3:
        return True
    f_val = max(0, min(255, f_val))
    roll = rng.randint(0,255)
    return roll < f_val

__all__ = ["attempt_capture","capture_chance","flee_success","CaptureResult"]
