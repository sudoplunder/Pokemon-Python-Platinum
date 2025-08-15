"""Runtime loader utilities for species data.

Provides cached access to per-species JSON documents produced by scripts.build_pokemon.
Focus: lightweight lookups for battle / party assembly without pulling full PokeAPI.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Iterable, Optional, List

from platinum.core.paths import POKEMON

_SPECIES_DIR = POKEMON / "species"
_INDEX_FILE = POKEMON / "species_index.json"

class SpeciesNotFound(Exception):
    pass

@lru_cache(maxsize=None)
def _index() -> list[int]:
    if not _INDEX_FILE.exists():
        return []
    return json.loads(_INDEX_FILE.read_text())

@lru_cache(maxsize=None)
def _species_path(species_id: int) -> Path:
    p = _SPECIES_DIR / f"{species_id:03}.json"
    if not p.exists():
        raise SpeciesNotFound(f"Species id {species_id} not found")
    return p

@lru_cache(maxsize=256)
def get_species(species_id: int) -> Dict[str, Any]:
    return json.loads(_species_path(species_id).read_text())

@lru_cache(maxsize=None)
def all_species_ids() -> Iterable[int]:
    return tuple(_index())

@lru_cache(maxsize=None)
def find_by_name(name: str) -> Optional[Dict[str, Any]]:
    name_lower = name.lower()
    for sid in all_species_ids():
        data = get_species(sid)
        if data["name"] == name_lower:
            return data
    return None

@lru_cache(maxsize=512)
def level_up_learnset(species_id: int) -> list[dict[str, Any]]:
    return list(get_species(species_id)["moves"]["level_up"])  # copy

@lru_cache(maxsize=512)
def machine_learnset(species_id: int) -> list[str]:
    return list(get_species(species_id)["moves"]["machines"])  # copy

# Evolution helpers -------------------------------------------------

def possible_evolutions(species_id: int, *, level: Optional[int]=None, item: Optional[str]=None,
                        friendship: Optional[int]=None, time_of_day: Optional[str]=None,
                        gender: Optional[str]=None, location_feature: Optional[str]=None) -> List[int]:
    """Return list of next evolution species ids whose conditions are satisfied.

    Parameters are optional; only those provided are considered for matching. A condition
    absent from the override is ignored. Friendship threshold assumed >= 220 if just present.
    """
    data = get_species(species_id)
    evo = data.get("evolution", {})
    details = evo.get("next_details") or []
    satisfied: List[int] = []
    for d in details:
        cond = d.get("conditions", {})
        trig = d.get("trigger")
        ok = True
        # Level
        lvl_req = cond.get("level")
        if lvl_req is not None and (level is None or level < int(lvl_req)):
            ok = False
        # Item
        item_req = cond.get("item")
        if item_req and (item is None or item_req != item):
            ok = False
        # Friendship
        if trig == "friendship":
            if friendship is None or friendship < cond.get("min", 220):
                ok = False
        # Time
        time_req = cond.get("time")
        if time_req and (time_of_day is None or time_of_day != time_req):
            ok = False
        # Gender
        gender_req = cond.get("gender")
        if gender_req and (gender is None or gender.lower() != gender_req.lower()):
            ok = False
        # Location feature (moss-rock / ice-rock etc.)
        loc_req = cond.get("feature")
        if loc_req and (location_feature is None or location_feature != loc_req):
            ok = False
        if ok:
            satisfied.append(d["id"])
    return satisfied

# Simple CLI for debugging
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        q = sys.argv[1]
        if q.isdigit():
            print(json.dumps(get_species(int(q)), indent=2))
        else:
            res = find_by_name(q)
            if not res:
                print("Not found", q)
            else:
                print(json.dumps(res, indent=2))
    else:
        print(f"Loaded {len(tuple(all_species_ids()))} species")
