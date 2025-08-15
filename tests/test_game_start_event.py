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
    # Inject a default choice for starter selection to avoid stdin usage
    # We modify the registered event action list directly for deterministic test.
    for evt in ctx.events.registry.events.values():
        for a in evt.actions:
            if a.get("command") == "CHOOSE_STARTER" and "choice" not in a:
                a["choice"] = 1
    ctx.events.dispatch_trigger({"type":"game_start"})
    # Capture output to ensure dialogue lines attempted (presence of key text)
    out = capsys.readouterr().out
    assert "Welcome to the world of Pokémon" in out or "[Missing dialogue: intro.start.1]" in out
    # Ensure tutorial battle placeholder and after-battle line occurred
    assert "tutorial_starly_1" in out  # battle placeholder id
    assert "after.battle" in out or "Your Pokémon really carried" in out
    assert "starter_chosen" in ctx.flags
    # Ensure flag set from event
    assert "story_started" in ctx.flags
