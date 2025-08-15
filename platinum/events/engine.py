from __future__ import annotations
from typing import Dict
from .registry import EventRegistry
from .types import Event
from . import scripts

class EventEngine:
    def __init__(self, context):
        self.context = context
        self.registry = EventRegistry()

    def register_batch(self, events):
        for e in events:
            self.registry.register(e)

    def dispatch_trigger(self, trigger: Dict):
        candidates = self.registry.events_for_trigger(trigger)
        fired_any = True
        # Loop allows cascading flags -> new events with same trigger type (rare)
        # but we limit iterations to avoid infinite loops.
        loops = 0
        while fired_any and loops < 5:
            fired_any = False
            for evt in candidates:
                if not evt.eligible(self.context.flags):
                    continue
                if not self._trigger_matches(evt.trigger, trigger):
                    continue
                self._execute(evt)
                fired_any = True
            loops += 1

    def _trigger_matches(self, event_trigger: Dict, trigger: Dict) -> bool:
        # Basic: type must match, and if value provided, must equal
        if event_trigger.get("type") != trigger.get("type"):
            return False
        v = event_trigger.get("value")
        if v is not None and v != trigger.get("value"):
            return False
        return True

    def _execute(self, event: Event):
        for action in event.actions:
            scripts.run_action(self.context, action)
        for f in event.set_flags:
            self.context.set_flag(f)
        for f in event.clear_flags:
            self.context.clear_flag(f)
        if event.once:
            event.fired = True

    # Flag propagation
    def on_flag_set(self, flag: str):
        # Dispatch pseudo-trigger for 'flag_set'
        self.dispatch_trigger({"type": "flag_set", "value": flag})