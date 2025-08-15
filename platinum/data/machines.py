"""Loader for TM/HM machine mappings (Gen IV)."""
from __future__ import annotations
import json
from functools import lru_cache
from typing import Dict, Any
from platinum.core.paths import MACHINES

@lru_cache(maxsize=None)
def get_machines_gen4() -> Dict[str, Dict[str, Any]]:
    path = MACHINES / "machines_gen4.json"
    if not path.exists():
        return {"tm": {}, "hm": {}}
    return json.loads(path.read_text())

__all__ = ["get_machines_gen4"]
