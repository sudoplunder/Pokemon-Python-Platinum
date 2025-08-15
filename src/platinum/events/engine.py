from __future__ import annotations
from typing import Dict, Iterable
from .model import Event
from .commands.base import registry
from ..core.logging import logger

class EventEngine:
    def __init__(self, context):
        self.context = context
        self._by_trigger: dict[str, list[Event]] = {}

    def register_batch(self, events: Iterable[Event]):
        for e in events:
            t = e.trigger.get("type")
            if t:
                self._by_trigger.setdefault(t, []).append(e)

    def dispatch(self, trigger: Dict):
        ttype = trigger.get("type")
        if not ttype:
            return
        candidates = self._by_trigger.get(ttype, [])
        fired_loop = True
        safety = 0
        while fired_loop and safety < 5:
            fired_loop = False
            for evt in candidates:
                if not evt.eligible(self.context.flags._flags):
                    continue
                if not self._matches(evt.trigger, trigger):
                    continue
                self._execute(evt)
                fired_loop = True
            safety += 1

    def on_flag_set(self, flag: str):
        self.dispatch({"type":"flag_set", "value":flag})

    def _matches(self, event_trigger: Dict, trigger: Dict) -> bool:
        if event_trigger.get("type") != trigger.get("type"):
            return False
        val = event_trigger.get("value")
        if val is not None and val != trigger.get("value"):
            return False
        return True

    def _execute(self, event: Event):
        logger.debug("Execute event", id=event.id)
        for action in event.actions:
            cmd = registry.get(action.command)
            if not cmd:
                logger.warn("Unknown command", command=action.command)
                continue
            cmd.execute(self.context, action.raw)
        for f in event.set_flags:
            self.context.set_flag(f)
        for f in event.clear_flags:
            self.context.clear_flag(f)
        if event.once:
            event.fired = True