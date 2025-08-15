"""Ability data loader (Gen I-IV subset)."""
from __future__ import annotations
import json
from functools import lru_cache
from typing import Dict, Any
from platinum.core.paths import ABILITIES

@lru_cache(maxsize=None)
def _index() -> list[str]:
    idx = ABILITIES / "abilities_index.json"
    if not idx.exists():
        return []
    return json.loads(idx.read_text())

@lru_cache(maxsize=None)
def get_ability(name: str) -> Dict[str, Any]:
    path = ABILITIES / f"{name}.json"
    if not path.exists():
        raise KeyError(f"Ability not found: {name}")
    return json.loads(path.read_text())

@lru_cache(maxsize=None)
def all_abilities() -> Dict[str, Dict[str, Any]]:
    return {a: get_ability(a) for a in _index()}

__all__ = ["get_ability","all_abilities"]
