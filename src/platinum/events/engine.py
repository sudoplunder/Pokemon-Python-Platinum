from .scripts import execute_script
class EventEngine:
    def __init__(self, registry, ctx):
        self.registry = registry
        self.ctx = ctx
        self.executed_once = set()
    def handle_trigger(self, trig_type: str, **payload):
        for evt in self.registry.candidates_for_trigger(trig_type):
            if not self._eligible(evt):
                continue
            execute_script(self.ctx, evt.script)
            for f in evt.set_flags: self.ctx.flags.set(f, True)
            for f in evt.clear_flags: self.ctx.flags.set(f, False)
            if evt.once: self.executed_once.add(evt.id)
    def invoke(self, event_id: str):
        evt = self.registry.by_id(event_id)
        if evt and self._eligible(evt):
            execute_script(self.ctx, evt.script)
            for f in evt.set_flags: self.ctx.flags.set(f, True)
            for f in evt.clear_flags: self.ctx.flags.set(f, False)
            if evt.once: self.executed_once.add(evt.id)
    def _eligible(self, evt):
        if evt.once and evt.id in self.executed_once:
            return False
        for p in evt.prerequisites:
            if p.startswith("!"):
                if self.ctx.flags.get(p[1:]): return False
            else:
                if not self.ctx.flags.get(p): return False
        return True
