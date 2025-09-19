from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, random
from typing import Dict, List, Optional, Literal, Tuple

EncounterMethod = Literal["grass","cave","water","old_rod"]

ASSET_ROOT = Path("assets/encounters")

@dataclass
class EncounterSlot:
    species: int
    min: int
    max: int
    weight: int
    time: Optional[List[str]] = None  # future use

    def level(self, rng: random.Random) -> int:
        if self.min == self.max:
            return self.min
        return rng.randint(self.min, self.max)

@dataclass
class EncounterMethodTable:
    base_rate: int
    slots: List[EncounterSlot]

@dataclass
class EncounterTable:
    zone: str
    methods: Dict[str, EncounterMethodTable]

_tables: Dict[str, EncounterTable] = {}

class EncounterLoadError(Exception):
    pass

def load_encounters(force: bool = False) -> Dict[str, EncounterTable]:
    if _tables and not force:
        return _tables
    _tables.clear()
    if not ASSET_ROOT.exists():
        return _tables
    for f in ASSET_ROOT.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            # Support lightweight redirect/deprecation stubs: {"deprecated_zone": "old", "redirect": "new"}
            if "zone" not in data:
                dep = data.get("deprecated_zone")
                redirect = data.get("redirect")
                if dep and redirect:
                    # Record an empty table so lookups on deprecated zone map to redirect target at call time
                    # We encode redirect mapping in a special zero-method table stored under deprecated name.
                    _tables[dep] = EncounterTable(zone=redirect, methods={})
                    continue
                else:
                    raise KeyError("zone")
            zone = data["zone"]
            methods: Dict[str, EncounterMethodTable] = {}
            for method_name, mdata in data.get("methods", {}).items():
                slots = [EncounterSlot(**slot) for slot in mdata.get("slots", [])]
                methods[method_name] = EncounterMethodTable(base_rate=mdata.get("base_rate",25), slots=slots)
            _tables[zone] = EncounterTable(zone=zone, methods=methods)
        except Exception as e:
            raise EncounterLoadError(f"Failed loading {f}: {e}") from e
    return _tables


def _resolve_zone(zone: str) -> str:
    """If zone entry is a redirect placeholder, follow it.

    We stored redirect placeholders as EncounterTable with methods = {} and zone field set to redirect target.
    """
    tables = load_encounters()
    tbl = tables.get(zone)
    if tbl and not tbl.methods and tbl.zone != zone:
        return tbl.zone
    return zone

def roll_encounter(zone: str, method: EncounterMethod, rng: Optional[random.Random] = None, *, time_of_day: Optional[str] = None) -> Optional[Tuple[int,int]]:
    rng = rng or random.Random()
    tables = load_encounters()
    zone = _resolve_zone(zone)
    tbl = tables.get(zone)
    if not tbl:
        return None
    m = tbl.methods.get(method)
    if not m or not m.slots:
        return None
    # Filter by time if provided
    slots = [s for s in m.slots if not s.time or (time_of_day and time_of_day in s.time)]
    if not slots:
        return None
    total_weight = sum(s.weight for s in slots)
    pick = rng.randint(1, total_weight)
    running = 0
    chosen: Optional[EncounterSlot] = None
    for s in slots:
        running += s.weight
        if pick <= running:
            chosen = s
            break
    if not chosen:
        return None
    lvl = chosen.level(rng)
    return chosen.species, lvl

def list_methods(zone: str) -> List[str]:
    tables = load_encounters()
    zone = _resolve_zone(zone)
    tbl = tables.get(zone)
    if not tbl:
        return []
    return sorted(tbl.methods.keys())

def available_methods(zone: str, *, has_old_rod: bool = False, has_surf: bool = False) -> List[str]:
    """Return encounter methods the player can actually select given progression.

    Rules (early-game simplified):
    - grass: always available
    - cave: always available (represents walking in cave tall grass equivalent)
    - old_rod: requires has_old_rod
    - water: requires has_surf
    """
    methods = list_methods(zone)
    allowed: List[str] = []
    for m in methods:
        if m == "old_rod" and not has_old_rod:
            continue
        if m == "water" and not has_surf:
            continue
        allowed.append(m)
    return allowed

def current_time_of_day(ctx) -> str:
    """Helper to return current time_of_day from GameContext state.

    Falls back to deriving from system clock if not set.
    """
    tod = getattr(ctx.state, 'time_of_day', None) if getattr(ctx, 'state', None) else None
    if tod:
        return tod
    import datetime
    hour = datetime.datetime.now().hour
    if 5 <= hour < 10:
        return 'morning'
    if 10 <= hour < 18:
        return 'day'
    if 18 <= hour < 22:
        return 'evening'
    return 'night'
