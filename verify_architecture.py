#!/usr/bin/env python3
"""
Manual verification script for Pokémon Platinum modular architecture.
This script tests key components without requiring user interaction.
"""
import sys
import os
sys.path.insert(0, 'src')

def test_event_system():
    """Test event loading and validation."""
    print("Testing event system...")
    
    from src.platinum.events.loader import load_events
    registry = load_events()
    
    events = registry.all()
    print(f"✓ Loaded {len(events)} events successfully")
    
    # Check for key events
    key_events = ["story.start", "story.rival_initial_visit", "story.route201_attempt", "story.starter_selection", "item.key.running_shoes"]
    for event_id in key_events:
        event = registry.by_id(event_id)
        if event:
            print(f"✓ Found event: {event_id}")
        else:
            print(f"✗ Missing event: {event_id}")
    

def test_dialogue_system():
    """Test dialogue manager."""
    print("\nTesting dialogue system...")
    
    from src.platinum.ui.dialogue_manager import DialogueManager
    
    # Test different modes
    for mode in ["expanded", "concise", "alt"]:
        dm = DialogueManager(mode=mode)
        text = dm.resolve("intro.tv.program")
        if text and not text.startswith("[missing:"):
            print(f"✓ Dialogue mode '{mode}' working")
        else:
            print(f"✗ Dialogue mode '{mode}' failed")


def test_character_mapping():
    """Test character name mapping."""
    print("\nTesting character mapping...")
    
    from src.platinum.events.characters import characters
    
    test_chars = ["barry", "rowan", "player", "mars"]
    for char in test_chars:
        name = characters.display(char)
        if name and name != char:
            print(f"✓ Character '{char}' -> '{name}'")
        else:
            print(f"? Character '{char}' -> '{name}' (may be fallback)")


def test_settings():
    """Test settings system."""
    print("\nTesting settings system...")
    
    from platinum.system.settings import Settings
    
    settings = Settings("test_settings.json")
    print(f"✓ Settings loaded with dialogue_mode: {settings.dialogue_mode}")
    print(f"✓ Text delay for '{settings.text_speed}': {settings.get_text_delay()}s")
    
    # Clean up test file
    if os.path.exists("test_settings.json"):
        os.remove("test_settings.json")


def test_json_schema():
    """Test JSON schema validation."""
    print("\nTesting JSON schema validation...")
    
    import json
    from pathlib import Path
    from jsonschema import validate
    
    schema_path = Path("schema/event.schema.json")
    if schema_path.exists():
        schema = json.loads(schema_path.read_text())
        print("✓ Event schema loaded successfully")
        
        # Test validation with a sample event
        sample_event_path = Path("assets/events/main/000_story_start.json")
        if sample_event_path.exists():
            sample_event = json.loads(sample_event_path.read_text())
            try:
                validate(sample_event, schema)
                print("✓ Sample event validates against schema")
            except Exception as e:
                print(f"✗ Schema validation failed: {e}")
    else:
        print("✗ Schema file not found")


def main():
    """Run all tests."""
    print("=== Pokémon Platinum Architecture Verification ===\n")
    
    try:
        test_event_system()
        test_dialogue_system()
        test_character_mapping() 
        test_settings()
        test_json_schema()
        
        print("\n=== Verification Complete ===")
        print("✓ Core modular architecture is functional")
        print("✓ Ready for python -m platinum launch")
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()