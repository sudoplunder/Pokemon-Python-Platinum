#!/usr/bin/env python3
"""
Test script to verify Growl move works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platinum.data.moves import get_move

def test_growl_move():
    """Test that Growl move has correct stat changes."""
    print("=== Growl Move Test ===")
    
    # Test loading the move data
    try:
        move_data = get_move("growl")
        if move_data:
            print(f"✅ Growl move loaded successfully")
            print(f"   Name: {move_data.get('display_name', 'Unknown')}")
            print(f"   Type: {move_data.get('type', 'Unknown')}")
            print(f"   Category: {move_data.get('category', 'Unknown')}")
            print(f"   Effect: {move_data.get('short_effect', 'Unknown')}")
            print(f"   Targets: {move_data.get('targets', 'Unknown')}")
            
            stat_changes = move_data.get('stat_changes', [])
            if stat_changes:
                print(f"✅ Stat changes defined:")
                for change in stat_changes:
                    stat = change.get('stat', 'Unknown')
                    change_val = change.get('change', 0)
                    chance = change.get('chance', 0)
                    print(f"     {stat}: {change_val:+d} (chance: {chance}%)")
            else:
                print("❌ No stat changes defined")
                
            flags = move_data.get('flags', {})
            if flags.get('sound'):
                print("✅ Sound flag set correctly")
            else:
                print("⚠️  Sound flag not set (should be true for Growl)")
                
        else:
            print("❌ Failed to load Growl move data")
            
    except Exception as e:
        print(f"❌ Error loading move data: {e}")
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_growl_move()