"""
Centralized path helpers (works with the current flat layout).
"""
from __future__ import annotations
from pathlib import Path

# This file lives at platinum/core/paths.py
ROOT = Path(__file__).resolve().parents[2]   # project root (one up from 'platinum')
ASSETS = ROOT / "assets"
DIALOGUE_EN = ASSETS / "dialogue" / "en"
EVENTS = ASSETS / "events"
SCHEMA = ROOT / "schema"
POKEMON = ASSETS / "pokemon"
POKEMON_RAW = POKEMON / "pokeapi_raw"
MOVES = ASSETS / "moves"
ABILITIES = ASSETS / "abilities"
ITEMS = ASSETS / "items"
MACHINES = ASSETS / "machines"