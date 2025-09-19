from __future__ import annotations
import json, os, time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Any
from platinum.core.logging import logger
from platinum.battle.experience import clamp_level
from platinum.battle.experience import required_exp_for_level

SAVE_DIR_NAME = ".platinum_saves"
LATEST_SYMLINK = "latest.txt"
ALT_LATEST_SYMLINK = "latest.xt"  # compatibility alias per UI request
MASTER_SAVE_FILENAME = "save_master.json"
TEMP_SAVE_FILENAME = "save_temp.json"

@dataclass
class PartyMember:
    species: str
    level: int = 5
    hp: int = 20
    max_hp: int = 20
    status: str | None = None
    exp: int = 0  # total accumulated experience (curve: n^3 placeholder)
    moves: list[str] = field(default_factory=list)  # learned move internal names (max 4 enforced on learn)
    move_pp: Dict[str, int] = field(default_factory=dict)  # remaining PP per move key (internal name)

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
    system_time: str = "00:00"  # last captured system clock HH:MM
    time_of_day: str = "day"     # enum: morning|day|evening|night

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
            # Migration: ensure exp baseline matches level threshold so XP gains level correctly
            try:
                need = required_exp_for_level(pm.level)
                if getattr(pm, 'exp', 0) < need:
                    pm.exp = need
            except Exception:
                pass
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
            version=data.get("version", 1),
            system_time=data.get("system_time", "00:00"),
            time_of_day=data.get("time_of_day", "day")
        )


def _save_dir() -> Path:
    home = Path(os.path.expanduser("~"))
    path = home / SAVE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

def _master_path() -> Path:
    return _save_dir() / MASTER_SAVE_FILENAME

def _temp_path() -> Path:
    return _save_dir() / TEMP_SAVE_FILENAME


def list_saves() -> List[Path]:
    """Single-file model: return the master file if it exists.

    Back-compat: callers that expect a list still get a list type.
    """
    p = _master_path()
    return [p] if p.exists() else []


def save_game(state: GameState) -> Path:
    """Write the single master save file and update pointer files."""
    d = _save_dir()
    state.last_save_ts = time.time()
    path = _master_path()
    path.write_text(json.dumps(state.to_json(), indent=2))
    # Update latest pointers (both names)
    (d / LATEST_SYMLINK).write_text(path.name)
    try:
        (d / ALT_LATEST_SYMLINK).write_text(path.name)
    except Exception:
        pass
    logger.info("GameSaved", file=str(path))
    return path

def save_temp(state: GameState) -> Path:
    """Write the temporary session save (not used for Continue)."""
    d = _save_dir()
    state.last_save_ts = time.time()
    path = _temp_path()
    path.write_text(json.dumps(state.to_json(), indent=2))
    logger.debug("GameTempSaved", file=str(path))
    return path

def delete_temp() -> None:
    """Delete the temporary session save if present."""
    try:
        p = _temp_path()
        if p.exists():
            p.unlink()
            logger.debug("GameTempDeleted", file=str(p))
    except Exception:
        pass

def save_game_slot(state: GameState, slot_index: int) -> Path:
    """Single-file model: ignore slot and save to master file."""
    return save_game(state)


def load_latest() -> GameState | None:
    d = _save_dir()
    master = _master_path()
    # Preferred: load master save
    if master.exists():
        try:
            data = json.loads(master.read_text())
            return GameState.from_json(data)
        except Exception as e:
            logger.error("GameLoadFailed", file=str(master), error=str(e))
            return None
    # Legacy pointers
    pointer = d / LATEST_SYMLINK
    if not pointer.exists():
        alt = d / ALT_LATEST_SYMLINK
        if alt.exists():
            pointer = alt
        else:
            # As last resort, try to find any legacy save_*.json
            legacy = sorted(d.glob("save_*.json"))
            if not legacy:
                return None
            fp = legacy[-1]
            try:
                data = json.loads(fp.read_text())
                # Migrate into master for future loads
                try:
                    master.write_text(json.dumps(data, indent=2))
                    (d / LATEST_SYMLINK).write_text(master.name)
                    try:
                        (d / ALT_LATEST_SYMLINK).write_text(master.name)
                    except Exception:
                        pass
                except Exception:
                    pass
                return GameState.from_json(data)
            except Exception as e:
                logger.error("GameLoadFailed", file=str(fp), error=str(e))
                return None
    # Try pointer target
    name = pointer.read_text().strip()
    fp = d / name
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text())
        # Migrate into master
        try:
            master.write_text(json.dumps(data, indent=2))
            (d / LATEST_SYMLINK).write_text(master.name)
            try:
                (d / ALT_LATEST_SYMLINK).write_text(master.name)
            except Exception:
                pass
        except Exception:
            pass
        return GameState.from_json(data)
    except Exception as e:
        logger.error("GameLoadFailed", file=str(fp), error=str(e))
        return None


def load_slot(index: int) -> GameState | None:
    """Single-file model: ignore slot index and return latest if present."""
    return load_latest()
