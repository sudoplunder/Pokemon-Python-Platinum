from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import math

# Placeholder minimal species data (to be replaced by PokéAPI ingestion)
SPECIES = {
    "turtwig": {"base_stats": {"hp":55,"atk":68,"def":64,"spa":45,"spd":55,"spe":31}, "types":["grass"]},
    "chimchar": {"base_stats": {"hp":44,"atk":58,"def":44,"spa":58,"spd":44,"spe":61}, "types":["fire"]},
    "piplup": {"base_stats": {"hp":53,"atk":51,"def":53,"spa":61,"spd":56,"spe":40}, "types":["water"]},
    "starly": {"base_stats": {"hp":40,"atk":55,"def":30,"spa":30,"spd":30,"spe":60}, "types":["normal","flying"]},
    "bidoof": {"base_stats": {"hp":59,"atk":45,"def":40,"spa":35,"spd":40,"spe":31}, "types":["normal"]},
    "shinx": {"base_stats": {"hp":45,"atk":65,"def":34,"spa":40,"spd":34,"spe":45}, "types":["electric"]},
    "budew": {"base_stats": {"hp":40,"atk":30,"def":35,"spa":50,"spd":70,"spe":55}, "types":["grass","poison"]},
    "kricketot": {"base_stats": {"hp":37,"atk":25,"def":41,"spa":25,"spd":41,"spe":25}, "types":["bug"]},
    "zubat": {"base_stats": {"hp":40,"atk":45,"def":35,"spa":30,"spd":40,"spe":55}, "types":["poison","flying"]},
    "geodude": {"base_stats": {"hp":40,"atk":80,"def":100,"spa":30,"spd":30,"spe":20}, "types":["rock","ground"]}
}

MOVES = {
    "tackle": {"power":40,"accuracy":100,"type":"normal","category":"physical"},
    "scratch": {"power":40,"accuracy":100,"type":"normal","category":"physical"},
    "ember": {"power":40,"accuracy":100,"type":"fire","category":"special","burn_chance":10},
    "water_gun": {"power":40,"accuracy":100,"type":"water","category":"special"},
    "vine_whip": {"power":45,"accuracy":100,"type":"grass","category":"physical"},
    "growl": {"power":0,"accuracy":100,"type":"normal","category":"status","stat_drop":{"atk":1}},
}

@dataclass
class Stats:
    hp: int
    atk: int
    def_: int
    spa: int
    spd: int
    spe: int

@dataclass
class Move:
    id: str
    power: int
    accuracy: int
    type: str
    category: str  # physical / special / status
    burn_chance: int = 0
    stat_drop: dict | None = None

@dataclass
class Pokemon:
    species: str
    level: int
    types: List[str]
    stats: Stats
    current_hp: int
    moves: List[Move]
    status: str | None = None

    def is_fainted(self) -> bool:
        return self.current_hp <= 0
    
    def as_save_dict(self):
        return {"species": self.species, "level": self.level, "hp": self.current_hp}

DEFAULT_LEARNSET = {
    "turtwig": ["tackle","growl","vine_whip"],
    "chimchar": ["scratch","ember","growl"],
    "piplup": ["tackle","water_gun","growl"],
}

def compute_stat(base: int, level: int, hp: bool=False) -> int:
    if hp:
        return math.floor(((2*base)*level)/100) + level + 10
    return math.floor(((2*base)*level)/100) + 5

def make_pokemon(species: str, level: int) -> Pokemon:
    sp = SPECIES[species]
    bs = sp["base_stats"]
    stats = Stats(
        hp=compute_stat(bs["hp"], level, hp=True),
        atk=compute_stat(bs["atk"], level),
        def_=compute_stat(bs["def"], level),
        spa=compute_stat(bs["spa"], level),
        spd=compute_stat(bs["spd"], level),
        spe=compute_stat(bs["spe"], level),
    )
    moves_ids = DEFAULT_LEARNSET.get(species, ["tackle"])[:4]
    moves = []
    for mid in moves_ids:
        mraw = MOVES[mid]
        moves.append(Move(id=mid, **mraw))
    return Pokemon(species=species, level=level, types=sp["types"], stats=stats, current_hp=stats.hp, moves=moves)