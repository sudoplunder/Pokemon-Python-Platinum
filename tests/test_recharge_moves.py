import random
from platinum.battle.core import BattleCore, Move
from platinum.battle.factory import battler_from_species
from platinum.battle.session import BattleSession, Party


def test_hyper_beam_recharge_flow():
    rng = random.Random(7)
    core = BattleCore(rng=rng)
    user = battler_from_species(399, 50)  # Bidoof
    # Durable foe so Hyper Beam doesn't end the battle immediately
    foe = battler_from_species(74, 80)    # Geodude high level
    hyper_beam = Move(name='Hyper Beam', type='normal', category='special', power=150, accuracy=100, flags={'recharge': True}, pp=5, max_pp=5)
    user.moves = [hyper_beam]
    foe.moves = [Move(name='Splash', type='normal', category='status', accuracy=None)]
    sess = BattleSession(Party([user]), Party([foe]), core=core)
    # Turn 1: use Hyper Beam
    sess.step(player_move_idx=0, enemy_move_idx=0)
    assert user.must_recharge is True
    # Turn 2: user must recharge, cannot act; message appears; flag clears after skip
    sess.step(player_move_idx=0, enemy_move_idx=0)
    assert any('must recharge' in s.lower() for s in sess.log)
    assert user.must_recharge is False
    # Turn 3: user acts again; flag becomes True again after using Hyper Beam
    sess.step(player_move_idx=0, enemy_move_idx=0)
    assert user.must_recharge is True