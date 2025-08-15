import random
import pytest
from platinum.battle.factory import battler_from_species
from platinum.battle.session import BattleSession, Party
from platinum.battle.core import BattleCore


def make_pp_empty(b):
    for m in b.moves:
        m.pp = 0


def test_struggle_triggers_and_recoil():
    rng = random.Random(123)
    # Use two low level species (Turtwig vs Starly ids 387, 396 as earlier examples)
    p = battler_from_species(387, 5)
    e = battler_from_species(396, 5)
    make_pp_empty(p)  # force Struggle for player
    # Enemy keep first move with PP so it can attack
    session = BattleSession(Party([p]), Party([e]), BattleCore(rng))
    assert p.current_hp is not None
    start_hp = p.current_hp
    session.step()  # player should use Struggle automatically
    # Ensure a log entry referencing Struggle exists
    assert any('Struggle' in line for line in session.log)
    assert p.current_hp is not None and p.current_hp < start_hp  # recoil or enemy damage should reduce HP


def test_capture_blocked_in_trainer_battle():
    rng = random.Random(1)
    p = battler_from_species(387, 5)
    e = battler_from_species(396, 5)
    session = BattleSession(Party([p]), Party([e]), BattleCore(rng), is_wild=False)
    assert session.attempt_capture('poke-ball') == 'NOT_ALLOWED'
