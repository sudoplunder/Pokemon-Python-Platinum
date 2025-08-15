from __future__ import annotations
import json
from pathlib import Path
from typing import List
from .model import Event, EventAction
from ..core.logging import logger
from ..core.errors import DataLoadError
from ..core.paths import EVENTS, SCHEMA

def _try_schema_validate(data: dict, path: Path):
    try:
        import jsonschema
    except Exception:
        return
    schema_path = SCHEMA / "event.schema.json"
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text())
    try:
        jsonschema.validate(data, schema)
    except Exception as e:
        raise DataLoadError(str(path), f"schema: {e}") from e

def load_events() -> List[Event]:
    if not EVENTS.exists():
        logger.warn("Events directory missing", path=str(EVENTS))
        return []
    results: List[Event] = []
    for file in sorted(EVENTS.rglob("*.json")):
        try:
            raw = json.loads(file.read_text())
            _try_schema_validate(raw, file)
            actions = [EventAction(a["command"], a) for a in raw.get("actions", [])]
            evt = Event(
                id=raw["id"],
                trigger=raw["trigger"],
                actions=actions,
                once=raw.get("once", True),
                set_flags=raw.get("set_flags", []),
                clear_flags=raw.get("clear_flags", []),
                prerequisites=raw.get("prerequisites")
            )
            results.append(evt)
        except Exception as e:
            logger.error("Event load failed", file=str(file), error=str(e))
    logger.info("Events loaded", count=len(results))
    return results