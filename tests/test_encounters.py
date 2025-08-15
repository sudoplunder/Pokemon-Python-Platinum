import random
from platinum.encounters.loader import load_encounters, roll_encounter, list_methods
from platinum.battle.session import BattleSession, Party
from platinum.battle.factory import battler_from_species


def test_methods_listed():
    load_encounters(force=True)
    methods = list_methods("route202")
    assert "grass" in methods and "old_rod" in methods


def test_roll_encounter_time_filter():
    rng = random.Random(1)
    # route202 has Kricketot only at morning/night; roll many daytime attempts should never pick species 401
    hits = set()
    for _ in range(50):
        res = roll_encounter("route202", "grass", rng=rng, time_of_day="day")
        assert res is not None
        hits.add(res[0])
    assert 401 not in hits


def test_roll_encounter_distribution_basic():
    rng = random.Random(42)
    counts = {}
    for _ in range(200):
        res = roll_encounter("route201", "grass", rng=rng)
        assert res is not None
        counts[res[0]] = counts.get(res[0],0)+1
    # Ensure at least two species appear and weights roughly respected (starter cameo rare)
    assert len(counts) >= 2
    assert counts.get(387,0) < counts.get(396,0)


def test_wild_battle_factory():
    rng = random.Random(99)
    player = Party([battler_from_species(387,5)])
    session = BattleSession.from_wild_encounter(player, "route201", "grass", rng=rng)
    assert session.is_wild
    assert session.enemy.active().species_id in {396,399,387}
