#!/usr/bin/env python3
"""Comprehensive test of the Route 201 boy event system."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_event_system_integration():
    """Test the complete event system integration."""
    print("🔧 Testing Event System Integration")
    print("=" * 60)
    
    try:
        # Import the actual game context and event system
        from platinum.cli import GameContext
        from platinum.system.settings import Settings
        from platinum.events.loader import load_events
        
        # Create a minimal settings object
        settings = Settings.load()
        
        # Create a real game context
        ctx = GameContext(settings)
        
        # Load events (this is critical!)
        events = load_events()
        ctx.events.register_batch(events)
        
        print(f"📋 Created game context")
        print(f"🎮 Events loaded: {len(events)}")
        print(f"🚩 Initial flags: {ctx.flags}")
        
        # Set required prerequisite flags
        print(f"\n🏠 Setting left_home flag...")
        ctx.set_flag("left_home")
        print(f"✅ left_home flag set")
        
        print(f"\n⚔️ Setting first_rival_battle_done flag...")
        ctx.set_flag("first_rival_battle_done")
        print(f"✅ first_rival_battle_done flag set")
        
        print(f"🚩 Current flags: {ctx.flags}")
        
        # Check initial inventory
        if not hasattr(ctx.state, 'inventory'):
            ctx.state.inventory = {}
        
        print(f"\n🎒 Initial inventory: {ctx.state.inventory}")
        
        # Now set the route201_boy_item flag (this should trigger the event)
        print(f"\n👦 Setting route201_boy_item flag...")
        print(f"📡 This should trigger the event automatically...")
        
        ctx.set_flag("route201_boy_item")
        
        print(f"✅ route201_boy_item flag set")
        print(f"🚩 Final flags: {ctx.flags}")
        print(f"🎒 Final inventory: {ctx.state.inventory}")
        
        # Check if potions were added
        if "potion" in ctx.state.inventory:
            print(f"✅ SUCCESS: Found {ctx.state.inventory['potion']} potions in inventory!")
        else:
            print(f"❌ FAILURE: No potions found in inventory")
            
        # Check if the follow-up flag was set
        if "route201_boy_item_given" in ctx.flags:
            print(f"✅ SUCCESS: route201_boy_item_given flag was set")
        else:
            print(f"❌ FAILURE: route201_boy_item_given flag was not set")
            
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        import traceback
        traceback.print_exc()

def check_event_loading():
    """Check if the route201 event is properly loaded."""
    print(f"\n📚 Checking Event Loading")
    print("=" * 60)
    
    try:
        from platinum.events.engine import EventEngine
        from platinum.cli import GameContext
        from platinum.system.settings import Settings
        from platinum.events.loader import load_events
        
        settings = Settings.load()
        ctx = GameContext(settings)
        
        # Load events
        events = load_events()
        ctx.events.register_batch(events)
        
        # Check registry
        registry_events = ctx.events.registry.events
        print(f"🎮 Total events in registry: {len(registry_events)}")
        
        # Look for the route201 boy event by checking all keys
        route201_event = None
        for trigger_key, event_list in registry_events.items():
            try:
                print(f"  Trigger: {trigger_key} -> {len(event_list)} events")
                for event in event_list:
                    if hasattr(event, 'id') and event.id == "route201.boy.gives.potions":
                        route201_event = event
                        break
            except Exception as e:
                print(f"  Trigger: {trigger_key} -> Error: {e}")
        
        if route201_event:
            print(f"✅ Found route201 boy event!")
            print(f"   ID: {route201_event.id}")
            print(f"   Trigger: {route201_event.trigger}")
            print(f"   Prerequisites: {route201_event.prerequisites}")
            print(f"   Once: {route201_event.once}")
            print(f"   Actions: {len(route201_event.actions)}")
        else:
            print(f"❌ Route201 boy event not found in loaded events")
            
    except Exception as e:
        print(f"❌ Error checking event loading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_event_loading()
    test_event_system_integration()
    
    print(f"\n🎯 Summary:")
    print(f"   If the integration test shows potions in inventory, the system works")
    print(f"   If not, there may be an issue with event loading or execution")