from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from ..core.logging import logger
from ..core.paths import LOCATIONS

@dataclass
class Location:
    id: str
    name: str
    adjacent: List[str]
    encounters: Dict[str, str]  # method -> encounter_table_id
    coord: tuple[int, int] | None = None

class LocationRegistry:
    def __init__(self):
        self._locations: Dict[str, Location] = {}
        self._load()
    
    def _load(self):
        if not LOCATIONS.exists():
            logger.warn("LocationsMissing", path=str(LOCATIONS))
            return
        for f in sorted(LOCATIONS.glob("*.json")):
            try:
                raw = json.loads(f.read_text())
                loc = Location(
                    id=raw["id"],
                    name=raw.get("name", raw["id"]),
                    adjacent=raw.get("adjacent", []),
                    encounters=raw.get("encounters", {}),
                    coord=tuple(raw.get("coord")) if raw.get("coord") else None
                )
                self._locations[loc.id] = loc
            except Exception as e:
                logger.error("LocationLoadFailed", file=str(f), error=str(e))
        logger.info("LocationsLoaded", count=len(self._locations))
    
    def get(self, loc_id: str) -> Optional[Location]:
        return self._locations.get(loc_id)
    
    def exists(self, loc_id: str) -> bool:
        return loc_id in self._locations