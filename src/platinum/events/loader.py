import json
from pathlib import Path
from jsonschema import validate
from .types import EventDef, Trigger, ScriptCommand
from .registry import EventRegistry
SCHEMA_PATH = Path("schema/event.schema.json")
EVENTS_ROOT = Path("assets/events")
def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
def coerce_event(obj: dict) -> EventDef:
    triggers = []
    for t in obj["triggers"]:
        t_copy = dict(t)
        t_type = t_copy.pop("type")
        triggers.append(Trigger(type=t_type, raw=t, **t_copy))
    script_cmds = []
    for c in obj["script"]:
        c_copy = dict(c)
        cmd = c_copy.pop("cmd")
        script_cmds.append(ScriptCommand(cmd=cmd, args=c_copy))
    return EventDef(
        id=obj["id"], category=obj["category"], phase=obj.get("phase",0),
        prerequisites=obj.get("prerequisites", []), triggers=triggers,
        script=script_cmds, once=obj.get("once", True),
        set_flags=obj.get("set_flags", []), clear_flags=obj.get("clear_flags", []),
        reward=obj.get("reward", {}), next_hints=obj.get("next_hints", [])
    )
def load_events(registry: EventRegistry | None = None) -> EventRegistry:
    schema = load_schema()
    registry = registry or EventRegistry()
    for path in EVENTS_ROOT.rglob("*.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        validate(obj, schema)
        evt = coerce_event(obj)
        registry.add(evt)
    return registry
if __name__ == "__main__":
    reg = load_events()
    print(f"Loaded {len(reg.all())} events.")
