#!/usr/bin/env python3
"""Test Route 201 boy in overworld mode to verify event loading fix."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_route201_in_overworld():
    """Test the Route 201 boy via overworld mode."""
    print("🌍 Testing Route 201 Boy in Overworld Mode")
    print("=" * 60)
    
    try:
        from platinum.cli import GameContext
        from platinum.system.settings import Settings
        from platinum.events.loader import load_events
        from platinum.system.save import GameState
        
        # Create game context
        settings = Settings.load()
        ctx = GameContext(settings)
        
        # Set up a basic game state like overworld mode would have
        ctx.state = GameState()
        ctx.state.player_name = "TestPlayer"
        ctx.state.location = "route_201_west"
        
        # Add basic inventory and party to simulate overworld mode
        ctx.state.inventory = {}
        ctx.state.party = ["dummy_pokemon"]  # Just need something for overworld check
        
        # Set required flags
        ctx.set_flag("left_home")
        ctx.set_flag("first_rival_battle_done")
        
        print(f"🎮 Initial state:")
        print(f"   Events loaded: {len(ctx.events.registry.events)}")
        print(f"   Flags: {ctx.flags}")
        print(f"   Inventory: {ctx.state.inventory}")
        
        # Simulate the overworld fix - check if events need loading
        if len(ctx.events.registry.events) == 0:
            print(f"\n🔄 Loading events (this should happen automatically now)...")
            events = load_events()
            ctx.events.register_batch(events)
            print(f"✅ Events loaded: {len(events)}")
        else:
            print(f"\n✅ Events already loaded: {len(ctx.events.registry.events)}")
        
        # Test the Route 201 boy interaction
        print(f"\n👦 Testing Route 201 boy interaction...")
        ctx.set_flag("route201_boy_item")
        
        print(f"\n🎯 Results:")
        print(f"   Final flags: {ctx.flags}")
        print(f"   Final inventory: {ctx.state.inventory}")
        
        if "potion" in ctx.state.inventory:
            print(f"✅ SUCCESS: Route 201 boy gave {ctx.state.inventory['potion']} potions!")
        else:
            print(f"❌ FAILURE: No potions received")
            
        if "route201_boy_item_given" in ctx.flags:
            print(f"✅ SUCCESS: Follow-up flag set correctly")
        else:
            print(f"❌ FAILURE: Follow-up flag not set")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_route201_in_overworld()