#!/usr/bin/env python3
"""Test Barry encounter music sequence."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_barry_music():
    """Test the Barry encounter music sequence."""
    print("🎵 Testing Barry Encounter Music Sequence")
    print("=" * 60)
    
    try:
        from platinum.cli import GameContext
        from platinum.system.settings import Settings
        from platinum.events.loader import load_events
        from platinum.system.save import GameState
        
        settings = Settings.load()
        ctx = GameContext(settings)
        
        # Load events
        events = load_events()
        ctx.events.register_batch(events)
        
        # Set up basic state
        ctx.state = GameState()
        ctx.state.player_name = "TestPlayer"
        ctx.state.inventory = {}
        
        # Set initial flags to trigger the event
        ctx.set_flag("rival_introduced")
        
        print(f"✅ Event system loaded with {len(events)} events")
        print(f"✅ Set up test context")
        
        # Check if the route201 event exists
        route201_event = None
        for event in events:
            if hasattr(event, 'id') and event.id == "route201.first_lake_plan":
                route201_event = event
                break
        
        if route201_event:
            print(f"✅ Found route201.first_lake_plan event")
            print(f"   Trigger: {route201_event.trigger}")
            print(f"   Actions: {len(route201_event.actions)}")
            
            # Look for music commands in the actions
            music_commands = []
            for i, action in enumerate(route201_event.actions):
                if action.get('command') == 'PLAY_MUSIC':
                    music_commands.append((i, action))
            
            print(f"   Music commands found: {len(music_commands)}")
            for i, (idx, action) in enumerate(music_commands):
                key = action.get('key', 'Unknown')
                loop = action.get('loop', True)
                snapshot = action.get('snapshot', False)
                print(f"     {i+1}. Action {idx}: {key} (loop={loop}, snapshot={snapshot})")
            
        else:
            print(f"❌ route201.first_lake_plan event not found")
            
        # Check if music files exist
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        
        music_files = [
            "encounter_barry_intro.ogg",
            "encounter_barry_loop.ogg", 
            "twinleaf_town.ogg"
        ]
        
        print(f"\n🎶 Checking music files:")
        for filename in music_files:
            path = root / "assets" / "audio" / "bgm" / filename
            if path.exists():
                print(f"   ✅ {filename}")
            else:
                print(f"   ❌ {filename} - NOT FOUND")
        
        print(f"\n🎯 Music Sequence Summary:")
        print(f"   1. Current twinleaf_town music is paused/snapshotted")
        print(f"   2. encounter_barry_intro.ogg plays (no loop) during mom's farewell")
        print(f"   3. Barry's dialogue appears with encounter_barry_loop.ogg (looping)")
        print(f"   4. After user presses Enter, twinleaf_town.ogg resumes")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_barry_music()