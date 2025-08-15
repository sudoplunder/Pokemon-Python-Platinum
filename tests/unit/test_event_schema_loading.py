from src.platinum.events.loader import load_events
def test_events_load_and_validate():
    reg = load_events()
    assert reg.by_id("story.start") is not None
    print("Test passed: Events load correctly and story.start event found")

if __name__ == "__main__":
    test_events_load_and_validate()
