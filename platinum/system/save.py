from __future__ import annotations
import json, os, time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Any
from platinum.core.logging import logger
from platinum.battle.experience import clamp_level

SAVE_DIR_NAME = ".platinum_saves"
LATEST_SYMLINK = "latest.txt"

@dataclass
class PartyMember:
    species: str
    level: int = 5
    hp: int = 20
    max_hp: int = 20
    status: str | None = None
    exp: int = 0  # total accumulated experience (curve: n^3 placeholder)
    moves: list[str] = field(default_factory=list)  # learned move internal names (max 4 enforced on learn)

@dataclass
class GameState:
    player_name: str = "PLAYER"
    rival_name: str = "RIVAL"
    player_gender: str = "unspecified"  # 'male','female','other','unspecified'
    assistant: str = "dawn"  # chosen assistant counterpart (dawn|lucas)
    money: int = 3000
    location: str = "twinleaf_town_bedroom"
    badges: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    party: List[PartyMember] = field(default_factory=list)
    pc_box: List[PartyMember] = field(default_factory=list)
    pokedex_seen: List[str] = field(default_factory=list)
    pokedex_caught: List[str] = field(default_factory=list)
    inventory: Dict[str, int] = field(default_factory=dict)
    play_time_seconds: int = 0
    last_save_ts: float = 0.0
    version: int = 1

    def to_json(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert PartyMember objects already handled by asdict
        return data

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "GameState":
        # Backward-compatible fill
        party = [PartyMember(**p) for p in data.get("party", [])]
        pc_box = [PartyMember(**p) for p in data.get("pc_box", [])]
        for pm in party + pc_box:
            pm.level = clamp_level(pm.level)
        return cls(
            player_name=data.get("player_name", "PLAYER"),
            rival_name=data.get("rival_name", "RIVAL"),
            player_gender=data.get("player_gender", data.get("gender", "unspecified")),
            assistant=data.get("assistant", "dawn" if data.get("player_gender", data.get("gender", "unspecified")) != "female" else "lucas"),
            money=data.get("money", 0),
            location=data.get("location", "unknown"),
            badges=data.get("badges", []),
            flags=data.get("flags", []),
            party=party,
            pc_box=pc_box,
            pokedex_seen=data.get("pokedex_seen", []),
            pokedex_caught=data.get("pokedex_caught", []),
            inventory=data.get("inventory", {}),
            play_time_seconds=data.get("play_time_seconds", 0),
            last_save_ts=data.get("last_save_ts", 0.0),
            version=data.get("version", 1)
        )


def _save_dir() -> Path:
    home = Path(os.path.expanduser("~"))
    path = home / SAVE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_saves() -> List[Path]:
    d = _save_dir()
    return sorted(d.glob("save_*.json"))


def save_game(state: GameState) -> Path:
    d = _save_dir()
    state.last_save_ts = time.time()
    # naive play time accumulation could be improved with session tracking
    existing = list_saves()
    idx = len(existing) + 1
    path = d / f"save_{idx:02d}.json"
    path.write_text(json.dumps(state.to_json(), indent=2))
    # Update latest pointer
    (d / LATEST_SYMLINK).write_text(path.name)
    logger.info("GameSaved", file=str(path))
    return path

def save_game_slot(state: GameState, slot_index: int) -> Path:
    """Overwrite specific slot (1-based). Creates intermediate slots if missing by appending until index reached."""
    d = _save_dir()
    state.last_save_ts = time.time()
    existing = list_saves()
    # If slot beyond existing count, just behave like append until we reach it
    if slot_index > len(existing):
        # append new
        path = d / f"save_{slot_index:02d}.json"
    else:
        path = existing[slot_index-1]
    path.write_text(json.dumps(state.to_json(), indent=2))
    (d / LATEST_SYMLINK).write_text(path.name)
    logger.info("GameSavedSlot", file=str(path), slot=slot_index)
    return path


def load_latest() -> GameState | None:
    d = _save_dir()
    pointer = d / LATEST_SYMLINK
    if not pointer.exists():
        return None
    name = pointer.read_text().strip()
    fp = d / name
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text())
        return GameState.from_json(data)
    except Exception as e:
        logger.error("GameLoadFailed", file=str(fp), error=str(e))
        return None


def load_slot(index: int) -> GameState | None:
    saves = list_saves()
    if index < 1 or index > len(saves):
        return None
    fp = saves[index-1]
    try:
        data = json.loads(fp.read_text())
        return GameState.from_json(data)
    except Exception as e:
        logger.error("GameLoadFailed", file=str(fp), error=str(e))
        return None
