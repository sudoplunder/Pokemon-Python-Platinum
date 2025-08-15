from platinum.events.loader import load_events
def test_events_load_and_validate():
    reg = load_events()
    assert reg.by_id("story.start") is not None
