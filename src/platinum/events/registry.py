from __future__ import annotations
from typing import Dict, List
from .types import EventDef
class EventRegistry:
    def __init__(self):
        self._events: Dict[str, EventDef] = {}
        self._triggers_index: Dict[str, List[EventDef]] = {}
    def add(self, event: EventDef):
        if event.id in self._events:
            raise ValueError(f"Duplicate event id {event.id}")
        self._events[event.id] = event
        for trig in event.triggers:
            key = trig.type
            self._triggers_index.setdefault(key, []).append(event)
    def by_id(self, event_id: str) -> EventDef | None:
        return self._events.get(event_id)
    def candidates_for_trigger(self, trig_type: str) -> List[EventDef]:
        return self._triggers_index.get(trig_type, [])
    def all(self) -> List[EventDef]:
        return list(self._events.values())
