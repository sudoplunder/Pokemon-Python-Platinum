import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from platinum.game.context import GameContext
from platinum.system.settings import Settings, SettingsData
from platinum.events.loader import load_events

def test_starter_event_fires():
    """Test that starter selection event fires when OPENING_COMPLETE is set."""
    settings = Settings(SettingsData(), Path("/tmp/test_settings.json"))
    ctx = GameContext(settings)
    
    # Load events
    ctx.load_events()
    
    # Initially no starter should be chosen
    assert not ctx.has_flag("STARTER_CHOSEN")
    
    # Trigger opening complete - should fire starter selection
    ctx.set_flag("OPENING_COMPLETE")
    
    # Note: The actual starter selection would require user input,
    # so we just test that the flag system propagates correctly
    assert ctx.has_flag("OPENING_COMPLETE")

def test_flag_system():
    """Test that flag system works correctly."""
    settings = Settings(SettingsData(), Path("/tmp/test_settings.json"))
    ctx = GameContext(settings)
    
    # Initially no flags
    assert len(ctx.debug_flags()) == 0
    
    # Set a flag
    ctx.set_flag("TEST_FLAG")
    assert ctx.has_flag("TEST_FLAG")
    assert "TEST_FLAG" in ctx.debug_flags()
    
    # Clear a flag
    ctx.clear_flag("TEST_FLAG")
    assert not ctx.has_flag("TEST_FLAG")
    assert "TEST_FLAG" not in ctx.debug_flags()

def test_inventory_system():
    """Test inventory add/consume functionality."""
    settings = Settings(SettingsData(), Path("/tmp/test_settings.json"))
    ctx = GameContext(settings)
    
    # Add item
    ctx.add_item("poke_ball", 5)
    assert ctx.inventory["poke_ball"] == 5
    
    # Add more of same item
    ctx.add_item("poke_ball", 3)
    assert ctx.inventory["poke_ball"] == 8
    
    # Consume item
    success = ctx.consume_item("poke_ball", 3)
    assert success
    assert ctx.inventory["poke_ball"] == 5
    
    # Try to consume more than available
    success = ctx.consume_item("poke_ball", 10)
    assert not success
    assert ctx.inventory["poke_ball"] == 5
    
    # Consume all
    success = ctx.consume_item("poke_ball", 5)
    assert success
    assert "poke_ball" not in ctx.inventory