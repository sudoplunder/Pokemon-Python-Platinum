"""Runtime loader for move data (Gen I-IV subset).

Provides simple cached access to parsed move JSON produced by scripts/build_moves.py.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from platinum.core.paths import MOVES

@lru_cache(maxsize=None)
def _index() -> list[str]:
    idx_path = MOVES / "moves_index.json"
    if not idx_path.exists():
        return []
    return json.loads(idx_path.read_text())

@lru_cache(maxsize=None)
def get_move(name: str) -> Dict[str, Any]:
    path = MOVES / f"{name}.json"
    if not path.exists():
        raise KeyError(f"Move not found: {name}")
    return json.loads(path.read_text())

@lru_cache(maxsize=None)
def all_moves() -> Dict[str, Dict[str, Any]]:
    return {m: get_move(m) for m in _index()}

__all__ = ["get_move","all_moves"]
