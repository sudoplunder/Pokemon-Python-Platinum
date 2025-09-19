#!/usr/bin/env python3
"""Test Route 201 first entry event with Barry dialogue."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_route201_first_entry():
    """Test the Route 201 first entry event with Barry dialogue."""
    print("🛣️ Testing Route 201 First Entry Event")
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
        ctx.state.location = "route_201"
        
        # Set the prerequisite flag
        ctx.set_flag("lake_plan_formed")
        
        print(f"✅ Set up context with lake_plan_formed flag")
        print(f"📍 Location: {ctx.state.location}")
        print(f"🚩 Initial flags: {sorted(list(ctx.flags))}")
        
        # Check if the route201 first entry event exists
        route201_entry_event = None
        for event in events:
            if hasattr(event, 'id') and event.id == "route201.first_entry":
                route201_entry_event = event
                break
        
        if route201_entry_event:
            print(f"✅ Found route201.first_entry event")
            print(f"   Trigger: {route201_entry_event.trigger}")
            print(f"   Prerequisites: {route201_entry_event.prerequisites}")
            print(f"   Actions: {len(route201_entry_event.actions)}")
            
            # Look for music and dialogue commands
            music_commands = []
            dialogue_commands = []
            for i, action in enumerate(route201_entry_event.actions):
                if action.get('command') == 'PLAY_MUSIC':
                    music_commands.append((i, action))
                elif action.get('command') == 'SHOW_TEXT':
                    dialogue_commands.append((i, action))
            
            print(f"   Music commands: {len(music_commands)}")
            for i, (idx, action) in enumerate(music_commands):
                key = action.get('key', 'Unknown')
                loop = action.get('loop', True)
                print(f"     {i+1}. Action {idx}: {key} (loop={loop})")
            
            print(f"   Dialogue commands: {len(dialogue_commands)}")
            for i, (idx, action) in enumerate(dialogue_commands):
                key = action.get('dialogue_key', 'Unknown')
                print(f"     {i+1}. Action {idx}: {key}")
                
        else:
            print(f"❌ route201.first_entry event not found")
            return
        
        # Now trigger the event by entering the map
        print(f"\n🎬 Triggering Route 201 first entry event...")
        
        trigger = {"type": "enter_map", "value": "route_201"}
        ctx.events.dispatch_trigger(trigger)
        
        print(f"\n✅ Event sequence completed!")
        print(f"🚩 Final flags: {sorted(list(ctx.flags))}")
        
        # Check if the expected flag was set
        if "route201_first_entry_done" in ctx.flags:
            print(f"✅ route201_first_entry_done flag set correctly")
        else:
            print(f"❌ route201_first_entry_done flag not set")
        
        print(f"\n🎯 Expected Music & Dialogue Sequence:")
        print(f"   1. Route 201 music pauses")
        print(f"   2. encounter_barry_intro.ogg plays (no loop)")
        print(f"   3. encounter_barry_loop.ogg starts looping")
        print(f"   4. 'Slow! Way too slow! Alright, let's head to the lake.' - Press Enter")
        print(f"   5. 'I've got dibs on the legendary Pokémon!' - Press Enter")
        print(f"   6. route_201.ogg resumes")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_route201_first_entry()