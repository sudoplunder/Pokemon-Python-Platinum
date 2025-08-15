from __future__ import annotations
import json, random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from ..core.logging import logger
from ..core.paths import ENCOUNTERS

@dataclass
class EncounterSlot:
    species: str
    rate: int
    min: int
    max: int

@dataclass
class EncounterTable:
    id: str
    method: str
    slots: List[EncounterSlot]
    _total: int = 0
    
    def finalize(self):
        self._total = sum(s.rate for s in self.slots)
    
    def choose(self, rng: random.Random) -> tuple[str, int]:
        if self._total <= 0:
            return (self.slots[0].species, self.slots[0].min)
        pick = rng.randint(1, self._total)
        acc = 0
        for s in self.slots:
            acc += s.rate
            if pick <= acc:
                lvl = rng.randint(s.min, s.max)
                return s.species, lvl
        s = self.slots[-1]
        return s.species, s.min

class EncounterRegistry:
    def __init__(self):
        self._tables: Dict[str, EncounterTable] = {}
        self._load()
    
    def _load(self):
        if not ENCOUNTERS.exists():
            logger.warn("EncountersMissing", path=str(ENCOUNTERS))
            return
        for f in sorted(ENCOUNTERS.glob("*.json")):
            try:
                raw = json.loads(f.read_text())
                slots = [EncounterSlot(**s) for s in raw.get("slots", [])]
                tbl = EncounterTable(id=raw["id"], method=raw.get("method", "grass"), slots=slots)
                tbl.finalize()
                self._tables[tbl.id] = tbl
            except Exception as e:
                logger.error("EncounterLoadFailed", file=str(f), error=str(e))
        logger.info("EncountersLoaded", count=len(self._tables))
    
    def get(self, table_id: str) -> Optional[EncounterTable]:
        return self._tables.get(table_id)