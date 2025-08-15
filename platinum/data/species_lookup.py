"""App-wide species lookup helpers.

Provides fast mapping between canonical lowercase species names and their dex IDs
for JSON assets under assets/pokemon/species (produced by build scripts).

Use `species_id(name_or_id)` when you have an arbitrary identifier that might
already be an int/digit string or a name; it returns an int dex id or raises.
Use `species_name(id_or_name)` to get the canonical lowercase name.

These wrappers sit atop loader.get_species / loader.find_by_name but maintain an
internal cached name->id dict built from the species index for O(1) lookups.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Iterable

from .loader import all_species_ids, get_species, find_by_name

class SpeciesLookupError(ValueError):
    pass

@lru_cache(maxsize=None)
def _name_to_id() -> dict[str,int]:
    mapping: dict[str,int] = {}
    # Build from index for speed
    for sid in all_species_ids():
        data = get_species(sid)
        mapping[data["name"].lower()] = sid  # ensure lowercase
    return mapping

@lru_cache(maxsize=None)
def _id_to_name() -> dict[int,str]:
    # Invert the mapping; building once is fine
    return {sid: name for name, sid in _name_to_id().items()}

def species_id(identifier: int | str) -> int:
    """Return dex id for identifier (int, digit string, or name).

    Raises SpeciesLookupError if unknown.
    """
    if isinstance(identifier, int):
        return identifier if identifier in _id_to_name() else _raise_id(identifier)
    s = str(identifier).strip().lower()
    if not s:
        raise SpeciesLookupError("Empty species identifier")
    if s.isdigit():
        val = int(s)
        return val if val in _id_to_name() else _raise_id(val)
    mapping = _name_to_id()
    if s in mapping:
        return mapping[s]
    # fallback to slow path (maybe name casing different, or newly added) 
    data = find_by_name(s)
    if data:
        return int(data["id"])  # refresh cache lazily? not needed
    raise SpeciesLookupError(f"Unknown species name '{identifier}'")

def species_name(identifier: int | str) -> str:
    """Return canonical lowercase name for dex id (int) or name.

    If already a valid name, returns lowercase canonical; else maps id->name.
    """
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        sid = int(identifier)
        names = _id_to_name()
        if sid not in names:
            _raise_id(sid)
        return names[sid]
    # treat as name
    return _normalize_name(identifier)

def _normalize_name(name: str) -> str:
    s = str(name).strip().lower()
    if not s:
        raise SpeciesLookupError("Empty species name")
    # Validate existence
    mapping = _name_to_id()
    if s not in mapping:
        data = find_by_name(s)
        if not data:
            raise SpeciesLookupError(f"Unknown species name '{name}'")
        # incorporate into cache mapping? (rare path) 
        mapping[s] = int(data["id"])  # update underlying dict
    return s

def _raise_id(sid: int):  # helper to unify raising
    raise SpeciesLookupError(f"Unknown species id {sid}")

__all__ = [
    "species_id",
    "species_name",
    "SpeciesLookupError",
]
