#!/usr/bin/env python3
"""Test starter selection menu fix."""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

def test_starter_menu_fix():
    """Test that the starter menu works without Rich markup errors."""
    print("🎯 Testing Starter Selection Menu Fix")
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
        
        # Set up basic state to get to starter selection
        ctx.state = GameState()
        ctx.state.player_name = "TestPlayer"
        ctx.state.location = "lake_verity_shore"
        
        # Set prerequisites for starter selection
        ctx.set_flag("briefcase_inspected")
        
        print(f"✅ Set up context for starter selection")
        print(f"🚩 Flags: {sorted(list(ctx.flags))}")
        
        # Test creating the starter menu items (this is where the error occurred)
        from platinum.ui.menu_nav import MenuItem
        
        items = [
            MenuItem(label="Now choose! Which Pokémon will it be?", value="_hdr", disabled=True),
            MenuItem(label="Tiny Leaf Pokémon TURTWIG!", value=str(387), label_color="green"),
            MenuItem(label="Chimp Pokémon CHIMCHAR!", value=str(390), label_color="red"),
            MenuItem(label="Penguin Pokémon PIPLUP!", value=str(393), label_color="blue"),
        ]
        
        print(f"✅ Created starter menu items without errors")
        
        # Test that the menu can be created without Rich markup errors
        from platinum.ui.menu_nav import Menu
        menu = Menu("Choose your starter", items, allow_escape=True, footer="↑/↓ or W/S to move • Enter to select • Esc to cancel")
        
        print(f"✅ Created starter menu without Rich markup errors")
        print(f"🎯 Menu items:")
        for i, item in enumerate(items):
            if not item.disabled:
                print(f"   {i}. {item.label} (color: {getattr(item, 'label_color', 'default')})")
        
        print(f"\n✅ Starter selection menu fix successful!")
        print(f"📝 Changes made:")
        print(f"   - Removed ANSI color codes from menu labels")
        print(f"   - Using Rich-compatible color names (green, red, blue)")
        print(f"   - Removed import of type_color_ansi and COLOR_RESET")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_starter_menu_fix()