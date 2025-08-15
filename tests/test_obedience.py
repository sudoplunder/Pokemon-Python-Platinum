from platinum.battle.core import Battler, Move, BattleCore, FieldState
from platinum.battle.obedience import level_cap_for_badges, disobedience_chance


def test_level_cap_mapping():
    assert level_cap_for_badges(0) == 20
    assert level_cap_for_badges(1) == 25
    assert level_cap_for_badges(7) == 55
    assert level_cap_for_badges(8) >= 999


def test_disobedience_probability_scaling():
    cap = 25
    assert disobedience_chance(25, cap) == 0
    assert 0 < disobedience_chance(26, cap) <= 0.5
    assert disobedience_chance(31, cap) == 0.5  # 6 levels over -> capped at 50%


def test_battler_disobeys(monkeypatch):
    mv = Move(name='Tackle', type='normal', category='physical', power=40, max_pp=35, pp=35)
    player = Battler(species_id=1, name='Test', level=35, types=('normal',), stats={'hp':40,'atk':30,'def':20,'sp_atk':10,'sp_def':10,'speed':15}, moves=[mv])
    enemy = Battler(species_id=2, name='Foe', level=5, types=('normal',), stats={'hp':30,'atk':10,'def':10,'sp_atk':5,'sp_def':5,'speed':5}, moves=[mv])
    # Set badge count low so cap is 25 and player is well above cap
    setattr(player, 'badge_count', 1)
    core = BattleCore()
    class DummyRng:
        def random(self): return 0.0
        def uniform(self, a, b): return a
        def randint(self, a, b): return a
    monkeypatch.setattr(core, 'rng', DummyRng())
    core.single_turn(player, mv, enemy, mv, FieldState())
    # Enemy should not have taken damage because player skipped turn
    assert enemy.current_hp == enemy.stats['hp']
