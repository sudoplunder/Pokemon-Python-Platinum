from platinum.battle.factory import battler_from_species
from platinum.battle.session import BattleSession, Party


def test_flee_basic():
    s = BattleSession(Party([battler_from_species(387,5)]), Party([battler_from_species(396,2)]))
    # High relative speed should allow flee after some attempts
    success = False
    for attempt in range(1,6):
        if s.attempt_flee(attempts=attempt):
            success = True
            break
    assert success
