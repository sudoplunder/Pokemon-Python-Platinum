#!/usr/bin/env python3
"""
Test script to verify victory music transitions work properly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platinum.audio.player import audio
from platinum.ui.battle import _play_victory_music
import time

def test_victory_music_transitions():
    """Test that victory music plays and stops properly."""
    print("=== Victory Music Transition Test ===")
    
    print("1. Playing route music...")
    try:
        audio.play_music("assets/audio/bgm/route_201.ogg", loop=True)
        audio.set_music_volume(0.7)
        print("   Route music started")
        time.sleep(2)
    except Exception as e:
        print(f"   Failed to play route music: {e}")
    
    print("2. Playing victory music...")
    try:
        _play_victory_music(is_trainer=True)
        print("   Victory music started")
        time.sleep(3)
    except Exception as e:
        print(f"   Failed to play victory music: {e}")
    
    print("3. Stopping victory music...")
    try:
        audio.stop_music()
        print("   Victory music stopped")
        time.sleep(0.5)
    except Exception as e:
        print(f"   Failed to stop music: {e}")
    
    print("4. Resuming route music...")
    try:
        audio.play_music("assets/audio/bgm/route_201.ogg", loop=True)
        audio.set_music_volume(0.7)
        print("   Route music resumed")
        time.sleep(2)
    except Exception as e:
        print(f"   Failed to resume route music: {e}")
    
    print("5. Final cleanup...")
    try:
        audio.stop_music()
        print("   All music stopped")
    except Exception as e:
        print(f"   Failed final cleanup: {e}")
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_victory_music_transitions()