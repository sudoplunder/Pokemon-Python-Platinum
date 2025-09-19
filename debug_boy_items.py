#!/usr/bin/env python3
"""Test the Route 201 boy item giving debug."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

# Mock context for testing
class MockState:
    def __init__(self):
        self.inventory = {}
        self.flags = set()

class MockContext:
    def __init__(self):
        self.state = MockState()
    
    def set_flag(self, flag):
        print(f"🚩 Setting flag: {flag}")
        self.state.flags.add(flag)
        # Simulate event dispatch
        print(f"📡 Would dispatch flag_set event for: {flag}")
    
    def has_flag(self, flag):
        return flag in self.state.flags

def debug_give_item():
    """Debug the GIVE_ITEM handler."""
    print("🔍 Debugging GIVE_ITEM Handler")
    print("=" * 50)
    
    from platinum.events.scripts import handle_give_item
    
    ctx = MockContext()
    
    # Test the exact action from the event file
    action = {
        "command": "GIVE_ITEM",
        "item": "Potions", 
        "key": "potion", 
        "amount": 3, 
        "pocket": "Medicine"
    }
    
    print(f"🎒 Before: {ctx.state.inventory}")
    print(f"🎮 Calling handle_give_item with action: {action}")
    
    try:
        handle_give_item(ctx, action)
        print(f"✅ Function completed")
        print(f"🎒 After: {ctx.state.inventory}")
        
        if "potion" in ctx.state.inventory:
            print(f"✅ Potions added: {ctx.state.inventory['potion']}")
        else:
            print(f"❌ No potions found in inventory")
            
    except Exception as e:
        print(f"❌ Error in handle_give_item: {e}")
        import traceback
        traceback.print_exc()

def test_flag_mechanism():
    """Test the flag setting mechanism."""
    print(f"\n🚩 Testing Flag Mechanism")
    print("=" * 50)
    
    ctx = MockContext()
    
    # Simulate dialogue action that sets the flag
    print(f"🗣️ Simulating boy dialogue...")
    print(f"💬 'I work at the Poke mart. Here, try these potions!'")
    
    # This is what happens when the dialogue action is processed
    flag_to_set = "route201_boy_item"
    
    print(f"🚩 Setting flag: {flag_to_set}")
    ctx.set_flag(flag_to_set)
    
    print(f"✅ Flag set, now event should trigger")
    print(f"📋 Current flags: {ctx.state.flags}")

def check_event_file():
    """Check if the event file can be loaded."""
    print(f"\n📄 Checking Event File")
    print("=" * 50)
    
    import json
    
    try:
        with open("assets/events/main/026_route201_boy_item.json", 'r') as f:
            event_data = json.load(f)
        
        print(f"✅ Event file loaded successfully")
        print(f"🆔 ID: {event_data['id']}")
        print(f"🎯 Trigger: {event_data['trigger']}")
        
        give_item_action = None
        for action in event_data.get('actions', []):
            if action.get('command') == 'GIVE_ITEM':
                give_item_action = action
                break
        
        if give_item_action:
            print(f"🎁 GIVE_ITEM action found: {give_item_action}")
        else:
            print(f"❌ No GIVE_ITEM action found")
            
        return event_data
        
    except Exception as e:
        print(f"❌ Error loading event file: {e}")
        return None

if __name__ == "__main__":
    debug_give_item()
    test_flag_mechanism()  
    check_event_file()
    
    print(f"\n🤔 Potential Issues:")
    print(f"   1. Event system not properly connecting flags to events")
    print(f"   2. GIVE_ITEM handler having errors but failing silently")
    print(f"   3. Event prerequisites not being met")
    print(f"   4. Audio/UI system errors preventing completion")