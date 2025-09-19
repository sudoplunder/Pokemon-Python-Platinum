#!/usr/bin/env python3
"""
Test Growl in a battle scenario to ensure it works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platinum.battle.session import BattleSession, Party
from platinum.battle.factory import battler_from_species
from platinum.battle.core import use_move

def test_growl_in_battle():
    """Test Growl in an actual battle scenario."""
    print("=== Growl Battle Test ===")
    
    try:
        # Create two test battlers
        player_battler = battler_from_species("bidoof", level=5)
        enemy_battler = battler_from_species("bidoof", level=5)
        
        # Create battle session
        player_party = Party([player_battler])
        enemy_party = Party([enemy_battler])
        session = BattleSession(player_party, enemy_party)
        
        print(f"Player Bidoof Attack: {player_battler.stats['attack']}")
        print(f"Enemy Bidoof Attack before Growl: {enemy_battler.stats['attack']}")
        
        # Find Growl move in player's moveset
        growl_move = None
        for move in player_battler.moves:
            if move.name.lower() == "growl":
                growl_move = move
                break
        
        if not growl_move:
            print("❌ Growl move not found in Bidoof's moveset")
            return
            
        print(f"✅ Found Growl move: {growl_move.name}")
        
        # Use Growl on enemy
        print("\n--- Using Growl ---")
        result = use_move(session, player_battler, growl_move, [enemy_battler])
        
        print(f"Enemy Bidoof Attack after Growl: {enemy_battler.stats['attack']}")
        print(f"Enemy Attack stages: {enemy_battler.stat_stages.get('attack', 0)}")
        
        # Check if attack was lowered
        if enemy_battler.stat_stages.get('attack', 0) < 0:
            print("✅ Growl successfully lowered enemy Attack!")
        else:
            print("❌ Growl did not lower enemy Attack")
            
    except Exception as e:
        print(f"❌ Error in battle test: {e}")
        import traceback
        traceback.print_exc()
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_growl_in_battle()