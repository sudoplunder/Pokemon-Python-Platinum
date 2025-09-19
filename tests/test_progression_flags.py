from platinum.system.settings import Settings
from platinum.cli import GameContext
from platinum.events.loader import load_events

def setup_ctx():
    settings = Settings.load()
    ctx = GameContext(settings)
    events = load_events()
    ctx.events.register_batch(events)
    # Ensure deterministic starter selection
    for evt in ctx.events.registry.events.values():
        for a in evt.actions:
            if a.get("command") == "CHOOSE_STARTER" and "choice" not in a:
                a["choice"] = 1
    return ctx

def test_pokedex_and_tour_progression(capsys):
    ctx = setup_ctx()
    ctx.events.dispatch_trigger({"type": "game_start"})
    ctx.set_flag("rival_introduced")
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "twinleaf_town_outside"})  # mom farewell + lake plan
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "lake_verity_shore"})
    ctx.events.dispatch_trigger({"type": "attempt_grass_entry", "value": "route_201"})  # starter + first battle
    assert "first_rival_battle_done" in ctx.flags
    # Running shoes gift
    ctx.events.dispatch_trigger({"type": "flag_set", "value": "first_rival_battle_done"})
    assert "received_running_shoes" in ctx.flags
    # Enter Sandgem lab for Pokédex
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "sandgem_lab"})
    assert "pokedex_received" in ctx.flags
    # Tour
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "sandgem_town"})
    assert "tour_complete" in ctx.flags

def test_rival_battle2_and_gym1_flags(capsys):
    ctx = setup_ctx()
    # Progress to post Pokédex
    ctx.events.dispatch_trigger({"type": "game_start"})
    ctx.set_flag("rival_introduced")
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "twinleaf_town_outside"})
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "lake_verity_shore"})
    ctx.events.dispatch_trigger({"type": "attempt_grass_entry", "value": "route_201"})
    ctx.events.dispatch_trigger({"type": "flag_set", "value": "first_rival_battle_done"})
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "sandgem_lab"})
    # Rival battle 2 route 203 requires Pokédex
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "route_203"})
    assert "rival_203_battle_done" in ctx.flags or "rival2_defeated" in ctx.flags
    # Arrive Oreburgh
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "oreburgh_city"})
    assert "oreburgh_arrived" in ctx.flags
    # Mine demo
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "oreburgh_mine_depths"})
    assert "leader_found" in ctx.flags
    # Gym start
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "oreburgh_gym"})
    assert "gym1_started" in ctx.flags
    # Simulate gym battle end
    ctx.events.dispatch_trigger({"type": "battle_end", "value": "roark_gym_battle"})
    assert "gym1_defeated" in ctx.flags and "coal_badge_obtained" in ctx.flags
