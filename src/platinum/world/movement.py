from __future__ import annotations
from platinum.core.logging import logger

def move_player(ctx, new_location: str):
    """Handle player movement to a new location."""
    if not ctx.locations.exists(new_location):
        logger.warn("InvalidLocation", location=new_location)
        return False
    
    old_location = ctx.player.location
    ctx.player.location = new_location
    logger.info("PlayerMoved", from_loc=old_location, to_loc=new_location)
    
    # Trigger location entry event
    ctx.events.dispatch({"type": "location_entry", "location": new_location})
    ctx.set_flag(f"ENTERED_{new_location.upper()}")
    
    return True

def check_random_encounter(ctx, location_id: str, method: str = "grass") -> bool:
    """Check if a random encounter should occur."""
    location = ctx.locations.get(location_id)
    if not location:
        return False
    
    encounter_table_id = location.encounters.get(method)
    if not encounter_table_id:
        return False
    
    # Simple 10% encounter rate
    if ctx.rng.random() > 0.1:
        return False
    
    encounter_table = ctx.encounters.get(encounter_table_id)
    if not encounter_table:
        logger.warn("MissingEncounterTable", table=encounter_table_id)
        return False
    
    species, level = encounter_table.choose(ctx.rng)
    ctx.battle_service.start_wild(species, level)
    return True