#!/usr/bin/env python3
"""Test the actual Barry encounter sequence."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_barry_encounter_flow():
    """Test the Barry encounter flow with music."""
    print("🎵 Testing Barry Encounter Flow")
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
        ctx.state.location = "twinleaf_town_outside"
        
        # Set the prerequisites for the Barry encounter
        ctx.set_flag("rival_introduced")
        
        print(f"✅ Set up context with rival_introduced flag")
        print(f"📍 Location: {ctx.state.location}")
        print(f"🚩 Flags: {sorted(list(ctx.flags))}")
        
        # Now trigger the event by entering the map
        print(f"\n🎬 Triggering Barry encounter event...")
        
        # This should trigger the route201.first_lake_plan event
        trigger = {"type": "enter_map", "value": "twinleaf_town_outside"}
        ctx.events.dispatch_trigger(trigger)
        
        print(f"\n✅ Event sequence completed!")
        print(f"🚩 Final flags: {sorted(list(ctx.flags))}")
        
        # Check if the expected flags were set
        if "left_home" in ctx.flags:
            print(f"✅ left_home flag set correctly")
        else:
            print(f"❌ left_home flag not set")
            
        if "lake_plan_formed" in ctx.flags:
            print(f"✅ lake_plan_formed flag set correctly")
        else:
            print(f"❌ lake_plan_formed flag not set")
        
        print(f"\n🎯 Music Sequence (should have executed):")
        print(f"   1. encounter_barry_intro.ogg played (no loop)")
        print(f"   2. Mom's farewell dialogue shown")
        print(f"   3. Barry's lake plan dialogue with encounter_barry_loop.ogg")
        print(f"   4. After Enter, twinleaf_town.ogg resumed")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_barry_encounter_flow()