from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from .types import Event

class EventRegistry:
    def __init__(self):
        self.events: Dict[str, Event] = {}
        self.by_trigger_type: Dict[str, List[Event]] = defaultdict(list)

    def register(self, event: Event):
        self.events[event.id] = event
        trig_type = event.trigger.get("type")
        if trig_type:
            self.by_trigger_type[trig_type].append(event)

    def events_for_trigger(self, trigger: dict) -> list[Event]:
        t = trigger.get("type")
        return list(self.by_trigger_type.get(t, []))