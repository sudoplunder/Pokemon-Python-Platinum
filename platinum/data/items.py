"""Item data loader (Gen I-IV subset)."""
from __future__ import annotations
import json
from functools import lru_cache
from typing import Dict, Any
from platinum.core.paths import ITEMS

@lru_cache(maxsize=None)
def _index() -> list[str]:
    idx = ITEMS / "items_index.json"
    if not idx.exists():
        return []
    return json.loads(idx.read_text())

@lru_cache(maxsize=None)
def get_item(name: str) -> Dict[str, Any]:
    path = ITEMS / f"{name}.json"
    if not path.exists():
        raise KeyError(f"Item not found: {name}")
    return json.loads(path.read_text())

@lru_cache(maxsize=None)
def all_items() -> Dict[str, Dict[str, Any]]:
    return {i: get_item(i) for i in _index()}

__all__ = ["get_item","all_items"]
