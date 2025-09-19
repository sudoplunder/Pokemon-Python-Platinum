from platinum.system.settings import Settings
from platinum.cli import GameContext
from platinum.events.loader import load_events

def test_game_start_triggers_intro(monkeypatch, capsys):
    settings = Settings.load()
    ctx = GameContext(settings)
    ctx.state.player_name = "Ash"
    ctx.state.rival_name = "Barry"
    events = load_events()
    ctx.events.register_batch(events)
    # Ensure deterministic starter selection
    for evt in ctx.events.registry.events.values():
        for a in evt.actions:
            if a.get("command") == "CHOOSE_STARTER" and "choice" not in a:
                a["choice"] = 1
    # Begin intro
    ctx.events.dispatch_trigger({"type": "game_start"})
    # Trigger bedroom enter to fire rival intro event
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "twinleaf_town_bedroom"})
    assert "rival_introduced" in ctx.flags
    # Player leaves house: entering outside map triggers farewell + plan event (sets left_home + lake_plan_formed)
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "twinleaf_town_outside"})
    assert "left_home" in ctx.flags
    assert "lake_plan_formed" in ctx.flags
    # 4) Go to lake (Cyrus encounter)
    ctx.events.dispatch_trigger({"type": "enter_map", "value": "lake_verity_shore"})
    # 5) Attempt to enter tall grass (Rowan intercept -> starter select + battle)
    ctx.events.dispatch_trigger({"type": "attempt_grass_entry", "value": "route_201"})
    out = capsys.readouterr().out
    # Intro text present
    assert "Welcome to the world of Pokémon" in out or "[Missing dialogue: intro.start.1]" in out
    # Ensure planned progression text occurred
    assert "tutorial_starly_1" in out  # battle id echoed
    assert "Your Pokémon really carried" in out or "after.battle" in out
    # Flags from sequence
    assert "lake_plan_formed" in ctx.flags
    assert "cyrus_lake_seen" in ctx.flags
    assert "starter_chosen" in ctx.flags
    assert "story_started" in ctx.flags
