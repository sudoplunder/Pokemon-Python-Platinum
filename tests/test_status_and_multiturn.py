import random
from platinum.battle.factory import battler_from_species
from platinum.battle.session import BattleSession, Party
from platinum.battle.core import BattleCore, Move


def run_turn(session: BattleSession, p_idx: int = 0, e_idx: int = 0):
    session.step(player_move_idx=p_idx, enemy_move_idx=e_idx)


def test_leer_lowers_defense():
    rng = random.Random(1)
    core = BattleCore(rng=rng)
    player_b = battler_from_species(399, 5)  # Bidoof
    # Inject Leer explicitly
    leer = Move(name='Leer', type='normal', category='status', accuracy=100,
                stat_changes=[{"stat": "defense", "change": -1, "chance": 100}])
    player_b.moves = [leer] + player_b.moves[:3]
    enemy_b = battler_from_species(396, 5)   # Starly target
    session = BattleSession(Party([player_b]), Party([enemy_b]), core=core)
    # Use Leer once (index 0)
    run_turn(session, p_idx=0, e_idx=0)
    # Defense stage of enemy should be -1
    assert session.enemy.active().stages.defense == -1
    # Log contains fell message
    assert any("defense" in s.lower() and "fell" in s.lower() for s in session.log)


def test_growl_lowers_attack():
    rng = random.Random(2)
    core = BattleCore(rng=rng)
    player_b = battler_from_species(396, 5)  # Starly
    growl = Move(name='Growl', type='normal', category='status', accuracy=100,
                 stat_changes=[{"stat": "attack", "change": -1, "chance": 100}])
    player_b.moves = [growl] + player_b.moves[:3]
    enemy_b = battler_from_species(399, 5)
    session = BattleSession(Party([player_b]), Party([enemy_b]), core=core)
    run_turn(session, p_idx=0, e_idx=0)
    assert session.enemy.active().stages.attack == -1
    assert any("attack" in s.lower() and "fell" in s.lower() for s in session.log)


def test_thunder_wave_ground_immunity():
    rng = random.Random(3)
    core = BattleCore(rng=rng)
    # Shinx vs Geodude; inject Thunder Wave explicitly
    player_b = battler_from_species(403, 10)
    twave = Move(name='Thunder Wave', type='electric', category='status', accuracy=100, ailment='paralysis', ailment_chance=100)
    player_b.moves = [twave] + player_b.moves[:3]
    enemy_b = battler_from_species(74, 10)
    session = BattleSession(Party([player_b]), Party([enemy_b]), core=core)
    # Use TWave; should not affect Ground target
    run_turn(session, p_idx=0, e_idx=0)
    assert session.enemy.active().status == 'none'
    assert any("doesn't affect" in s.lower() for s in session.log)


def test_solarbeam_two_turns():
    rng = random.Random(4)
    core = BattleCore(rng=rng)
    player_b = battler_from_species(315, 50)  # Roselia
    mv = Move(name='SolarBeam', type='grass', category='special', power=120, accuracy=100, flags={'charge': True})
    player_b.moves = [mv] + player_b.moves[:3]
    # Enemy Magikarp with Splash to avoid interfering damage/priority and ensure Grass is effective
    enemy_b = battler_from_species(129, 5)
    splash = Move(name='Splash', type='normal', category='status', accuracy=None)
    enemy_b.moves = [splash] + enemy_b.moves[:3]
    session = BattleSession(Party([player_b]), Party([enemy_b]), core=core)
    # Turn 1: begins charging, no damage (enemy splashes)
    run_turn(session, p_idx=0, e_idx=0)
    assert session.player.active().charging_move is not None
    # Turn 2: unleashes
    run_turn(session, p_idx=0, e_idx=0)
    joined = "\n".join(session.log).lower()
    assert "began charging" in joined and "unleashes" in joined and "used solarbeam" in joined
    # Charging state should be cleared after release
    assert session.player.active().charging_move is None
    # Log contains began charging then unleashes
    joined = "\n".join(session.log).lower()
    assert "began charging" in joined and "unleashes" in joined
