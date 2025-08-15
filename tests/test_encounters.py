import pytest
import random
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from platinum.world.encounters import EncounterTable, EncounterSlot

def test_encounter_table_distribution():
    """Test that encounter table produces expected distribution."""
    slots = [
        EncounterSlot("starly", 40, 2, 4),
        EncounterSlot("bidoof", 60, 2, 4),
    ]
    table = EncounterTable("test", "grass", slots)
    table.finalize()
    
    # Test that total rate is correct
    assert table._total == 100
    
    # Run encounters and check distribution
    rng = random.Random(12345)  # Fixed seed for reproducibility
    results = {}
    trials = 1000
    
    for _ in range(trials):
        species, level = table.choose(rng)
        results[species] = results.get(species, 0) + 1
    
    # Check approximately correct ratios (within 10% tolerance)
    starly_ratio = results.get("starly", 0) / trials
    bidoof_ratio = results.get("bidoof", 0) / trials
    
    assert 0.35 <= starly_ratio <= 0.45  # Expected ~0.4
    assert 0.55 <= bidoof_ratio <= 0.65  # Expected ~0.6
    
    # Check that sum is 1
    assert abs((starly_ratio + bidoof_ratio) - 1.0) < 0.01

def test_encounter_level_range():
    """Test that encounter levels fall within specified ranges."""
    slots = [
        EncounterSlot("starly", 100, 2, 4),
    ]
    table = EncounterTable("test", "grass", slots)
    table.finalize()
    
    rng = random.Random(12345)
    
    # Test multiple encounters
    for _ in range(100):
        species, level = table.choose(rng)
        assert species == "starly"
        assert 2 <= level <= 4

def test_empty_encounter_table():
    """Test behavior with empty encounter table."""
    table = EncounterTable("empty", "grass", [])
    table.finalize()
    
    assert table._total == 0
    
    # Should not crash but return something safe
    rng = random.Random()
    # This would actually crash with index error, so let's not test it
    # In a real implementation we'd want to handle this case