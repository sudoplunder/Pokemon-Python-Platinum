from __future__ import annotations
import json
from pathlib import Path
from typing import List
from platinum.core.paths import ASSETS
from .types import Event

def load_events() -> List[Event]:
    """Load all event JSON files.

    Uses the absolute assets path so it is robust to invoking the game from
    different working directories (e.g. running inside the `platinum` package
    folder instead of project root).
    """
    root = ASSETS / "events"
    results: List[Event] = []
    if not root.exists():
        return results
    for f in sorted(root.rglob("*.json")):
        try:
            data = json.loads(f.read_text())
            evt = Event(
                id=data["id"],
                trigger=data["trigger"],
                actions=data["actions"],
                once=data.get("once", True),
                set_flags=data.get("set_flags", []),
                clear_flags=data.get("clear_flags", []),
                prerequisites=data.get("prerequisites")
            )
            results.append(evt)
        except Exception as e:
            print(f"[events] Failed to load {f}: {e}")
    return results