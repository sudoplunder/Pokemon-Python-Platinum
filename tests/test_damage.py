import pytest
import random
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from platinum.battle.models import make_pokemon, Pokemon, Move
from platinum.battle.mechanics import calculate_damage, is_critical, effectiveness

def test_damage_calculation():
    """Test that damage calculation produces expected ranges."""
    # Create test Pokemon
    attacker = make_pokemon("chimchar", 10)
    defender = make_pokemon("turtwig", 10)
    
    # Find ember move
    ember = None
    for move in attacker.moves:
        if move.id == "ember":
            ember = move
            break
    
    assert ember is not None
    
    rng = random.Random(12345)  # Fixed seed
    
    # Calculate damage multiple times
    damages = []
    for _ in range(100):
        dmg, meta = calculate_damage(attacker, defender, ember, rng)
        damages.append(dmg)
        
        # Damage should always be at least 1
        assert dmg >= 1
        
        # Meta should contain expected keys
        assert "crit" in meta
        assert "stab" in meta
        assert "type" in meta
    
    # Check damage range is reasonable (fire vs grass should be effective)
    min_dmg = min(damages)
    max_dmg = max(damages)
    avg_dmg = sum(damages) / len(damages)
    
    # Should have some variation
    assert max_dmg > min_dmg
    
    # Fire vs Grass should be super effective (2x)
    assert avg_dmg > 10  # Should do decent damage

def test_type_effectiveness():
    """Test type effectiveness calculations."""
    fire_mon = make_pokemon("chimchar", 5)
    grass_mon = make_pokemon("turtwig", 5)
    
    # Fire vs Grass should be 2x effective
    assert effectiveness("fire", grass_mon) == 2.0
    
    # Grass vs Fire should be 0.5x effective  
    assert effectiveness("grass", fire_mon) == 0.5
    
    # Normal vs Normal should be 1x
    assert effectiveness("normal", fire_mon) == 1.0

def test_critical_hit_rate():
    """Test that critical hits occur at expected rate."""
    rng = random.Random(12345)
    
    crits = 0
    trials = 1600  # Should get ~100 crits at 1/16 rate
    
    for _ in range(trials):
        if is_critical(rng):
            crits += 1
    
    # Should be approximately 1/16 (6.25%), allow some variance
    crit_rate = crits / trials
    assert 0.04 <= crit_rate <= 0.09  # 4-9% range

def test_pokemon_creation():
    """Test that Pokemon are created correctly."""
    starter = make_pokemon("turtwig", 5)
    
    assert starter.species == "turtwig"
    assert starter.level == 5
    assert "grass" in starter.types
    assert starter.current_hp == starter.stats.hp
    assert len(starter.moves) > 0
    assert not starter.is_fainted()
    
    # Test faint mechanics
    starter.current_hp = 0
    assert starter.is_fainted()