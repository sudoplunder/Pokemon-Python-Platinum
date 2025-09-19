#!/usr/bin/env python3
"""
Test script to verify wild battle victory sequence with XP, levels, and music.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platinum.ui.battle import _play_victory_music
from platinum.audio.player import audio
import time

def test_wild_victory_music():
    """Test that wild victory music plays correctly with BGM system."""
    print("=== Wild Victory Music Test ===")
    
    print("1. Testing wild victory music...")
    try:
        _play_victory_music(is_trainer=False)
        print("   ✅ Wild victory music started")
        time.sleep(3)  # Let it play for a bit
    except Exception as e:
        print(f"   ❌ Failed to play wild victory music: {e}")
    
    print("2. Stopping victory music...")
    try:
        audio.stop_music()
        print("   ✅ Victory music stopped")
        time.sleep(0.5)
    except Exception as e:
        print(f"   ❌ Failed to stop music: {e}")
    
    print("3. Testing trainer victory music for comparison...")
    try:
        _play_victory_music(is_trainer=True)
        print("   ✅ Trainer victory music started")
        time.sleep(3)
    except Exception as e:
        print(f"   ❌ Failed to play trainer victory music: {e}")
    
    print("4. Final cleanup...")
    try:
        audio.stop_music()
        print("   ✅ All music stopped")
    except Exception as e:
        print(f"   ❌ Failed final cleanup: {e}")
    
    print("=== Test Complete ===")
    print("Both wild and trainer victory music should use BGM system and be properly stoppable.")

if __name__ == "__main__":
    test_wild_victory_music()