from platinum.battle.factory import battler_from_species
from platinum.battle.session import BattleSession, Party


def test_basic_player_wins():
    player_party = Party([battler_from_species(387, 5)])  # Turtwig
    enemy_party = Party([battler_from_species(396, 2)])   # Starly
    session = BattleSession(player_party, enemy_party)
    outcome = session.run_auto()
    assert outcome == "PLAYER_WIN"
    # Ensure log captured at least one attack message
    assert any('used' in line.lower() for line in session.log)
