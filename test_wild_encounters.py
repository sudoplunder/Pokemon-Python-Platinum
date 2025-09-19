#!/usr/bin/env python3
"""
Test script to verify wild encounter levels are properly specified.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platinum.encounters.loader import roll_encounter, load_encounters
import random

def test_wild_encounter_levels():
    """Test that wild encounters properly generate levels within specified ranges."""
    print("=== Wild Encounter Level Test ===")
    
    # Load encounter tables
    try:
        tables = load_encounters()
        print(f"✅ Loaded {len(tables)} encounter zones")
    except Exception as e:
        print(f"❌ Failed to load encounters: {e}")
        return
    
    # Test Route 201 encounters
    test_zone = "route201"
    test_method = "grass"
    
    print(f"\n--- Testing {test_zone} {test_method} encounters ---")
    
    if test_zone not in tables:
        print(f"❌ Zone {test_zone} not found")
        return
        
    table = tables[test_zone]
    if test_method not in table.methods:
        print(f"❌ Method {test_method} not found in {test_zone}")
        return
        
    method_table = table.methods[test_method]
    print(f"✅ Found encounter table with {len(method_table.slots)} slots")
    
    # Show expected level ranges
    for i, slot in enumerate(method_table.slots):
        print(f"   Slot {i+1}: Species {slot.species}, Level {slot.min}-{slot.max}, Weight {slot.weight}")
    
    # Test multiple encounters
    print(f"\n--- Rolling 10 encounters ---")
    rng = random.Random(42)  # Fixed seed for reproducible tests
    
    for i in range(10):
        result = roll_encounter(test_zone, test_method, rng=rng)
        if result:
            species, level = result
            print(f"   Encounter {i+1}: Species {species}, Level {level}")
            
            # Verify level is within expected range
            valid_level = False
            for slot in method_table.slots:
                if slot.species == species and slot.min <= level <= slot.max:
                    valid_level = True
                    break
            
            if valid_level:
                print(f"      ✅ Level {level} is within valid range for species {species}")
            else:
                print(f"      ❌ Level {level} is outside valid range for species {species}")
        else:
            print(f"   Encounter {i+1}: No encounter")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_wild_encounter_levels()