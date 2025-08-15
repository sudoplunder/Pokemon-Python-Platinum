from __future__ import annotations
from dataclasses import dataclass, field
import random
import os
from typing import List, Dict, Optional
from ..core.flags import FlagSet
from ..events.engine import EventEngine
from ..events.loader import load_events
from ..dialogue.manager import DialogueManager
from ..system.settings import Settings
from ..system.save import SaveStore
from ..battle.service import BattleService
from ..world.locations import LocationRegistry
from ..world.encounters import EncounterRegistry

@dataclass
class PlayerState:
    location: str = "twinleaf_town"
    money: int = 3000

class GameContext:
    def __init__(self, settings: Settings, rng: Optional[random.Random] = None):
        self.settings = settings
        self.rng = rng or self._create_rng()
        self.events = EventEngine(self)
        self.flags = FlagSet(self.events)
        self.dialogue = DialogueManager(settings)
        self.save_store = SaveStore()
        self.player = PlayerState()
        self.inventory: Dict[str, int] = {}
        self.party: List = []  # Pokemon instances
        self.battle_service = BattleService(self)
        self.locations = LocationRegistry()
        self.encounters = EncounterRegistry()

    def _create_rng(self) -> random.Random:
        """Create RNG with optional seed from environment."""
        seed = os.environ.get('PLAT_RNG_SEED')
        if seed:
            try:
                seed = int(seed)
            except ValueError:
                seed = None
        return random.Random(seed)

    # Convenience wrappers
    def set_flag(self, f: str):
        self.flags.set(f)
    
    def has_flag(self, f: str) -> bool:
        return self.flags.has(f)
    
    def clear_flag(self, f: str):
        self.flags.clear(f)
    
    def add_item(self, item: str, qty: int = 1):
        self.inventory[item] = self.inventory.get(item, 0) + qty
    
    def consume_item(self, item: str, qty: int = 1) -> bool:
        if self.inventory.get(item, 0) < qty:
            return False
        self.inventory[item] -= qty
        if self.inventory[item] <= 0:
            self.inventory.pop(item, None)
        return True

    def load_events(self):
        evts = load_events()
        self.events.register_batch(evts)

    def save(self):
        data = {
            "flags": sorted(list(self.flags._flags)),
            "player": self.player.__dict__,
            "inventory": self.inventory,
            "party": [p.as_save_dict() for p in self.party],
        }
        self.save_store.write(data)

    def load(self) -> bool:
        data = self.save_store.read()
        if not data:
            return False
        for f in data.get("flags", []):
            self.flags.set(f, propagate=False)
        p = data.get("player") or {}
        self.player.location = p.get("location", self.player.location)
        self.player.money = p.get("money", self.player.money)
        self.inventory = data.get("inventory", {})
        # Party reconstruction placeholder (species minimal)
        from ..battle.models import make_pokemon
        self.party = []
        for entry in data.get("party", []):
            self.party.append(make_pokemon(entry["species"], entry.get("level", 5)))
        return True
    
    def debug_flags(self):
        return sorted(self.flags._flags)