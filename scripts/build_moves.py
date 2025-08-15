"""Extract Gen I-IV move data from PokeAPI raw dumps into concise JSON files.

Input: assets/pokemon/pokeapi_raw/pokeapi.co_api_v2_move_*.json
Output: assets/moves/{move_name}.json (only moves whose originating generation <= 4)
Also writes an index file moves_index.json listing all move slugs included.

Captured fields (expanded mechanics subset):
{
  "name": str,            # slug
  "display_name": str,    # capitalized with spaces
  "type": str,
  "category": str,        # physical|special|status
  "power": int|null,
  "accuracy": int|null,
  "pp": int|null,
  "priority": int,
  "generation": int,
  "crit_rate_stage": int, # 0 normal, 1+ for high-crit moves
  "targets": str,         # simplified target type (raw API target name)
  "short_effect": str,    # english short_effect text (trimmed)
  "effect": str,          # full effect text (english)
  "drain": [int,int]|null, # numerator, denominator heal fraction of damage dealt (e.g., 1,2 for 50%)
  "recoil": [int,int]|null,# numerator, denominator recoil fraction
  "multi_hit": [int,int]|null, # min,max hits
  "multi_turn": [int,int]|null,# min,max charging/binding turns
  "flinch_chance": int,   # percentage
  "ailment": str|null,    # status ailment slug
  "ailment_chance": int,  # percentage
  "stat_changes": [ {"stat": str, "change": int, "chance": int } ]
  "flags": {              # boolean battle flags
      "contact": bool,
      "sound": bool,
      "punch": bool,
      "bite": bool,
      "powder": bool,
      "pulse": bool,
      "ballistic": bool,
      "gravity": bool,     # blocked by gravity
      "snatch": bool,
      "mirror": bool,      # eligible for Mirror Move / Copycat
      "protect": bool,     # blocked by Protect/Detect
      "magic_coat": bool,  # reflectable
      "defrost": bool      # can thaw user
  }
}

High-crit detection: move.meta.crit_rate > 0.
Drain/Recoil/Multi-hit/etc now captured.

Usage: python scripts/build_moves.py
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Dict, Any, List

from platinum.core.paths import POKEMON_RAW, MOVES, ASSETS

GENERATION_NAME_TO_NUM = {
    "generation-i": 1,
    "generation-ii": 2,
    "generation-iii": 3,
    "generation-iv": 4,
    "generation-v": 5,
    "generation-vi": 6,
    "generation-vii": 7,
    "generation-viii": 8,
    "generation-ix": 9,
}

MOVE_FILE_RX = re.compile(r"pokeapi\.co_api_v2_move_(.+)\.json$")

HIGH_CRIT_MOVES = {
    # Some legacy high-crit moves also flagged via meta.crit_rate but include set for safety if PokeAPI data missing.
    "slash","night-slash","aeroblast","air-cutter","cross-chop","drill-run","leaf-blade","poison-tail",
    "psycho-cut","shadow-claw","spacial-rend","stone-edge","crabhammer","razor-leaf","razor-wind","karate-chop"
}

def _load_moves() -> List[Path]:
    return sorted(POKEMON_RAW.glob("pokeapi.co_api_v2_move_*.json"))


def _norm_display(name: str) -> str:
    return name.replace("-", " ").title()


def build_moves():
    MOVES.mkdir(parents=True, exist_ok=True)
    index: List[str] = []
    for p in _load_moves():
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        gen_name = data.get("generation", {}).get("name")
        if not gen_name:
            continue
        gen_num = GENERATION_NAME_TO_NUM.get(gen_name)
        if not gen_num or gen_num > 4:
            continue  # Only keep <= Gen IV
        name = data.get("name")
        if not name:
            continue
        dmg_class = data.get("damage_class", {}).get("name") or "status"
        power = data.get("power")
        acc = data.get("accuracy")
        pp = data.get("pp")
        priority = data.get("priority", 0)
        meta = data.get("meta") or {}
        crit_stage = 1 if (meta.get("crit_rate", 0) or 0) > 0 or name in HIGH_CRIT_MOVES else 0
        target = data.get("target", {}).get("name") or "selected-pokemon"
        # Pull English effect entries
        short_effect = ""; full_effect = ""
        for eff in data.get("effect_entries", []):
            if eff.get("language", {}).get("name") == "en":
                short_effect = eff.get("short_effect", "")
                full_effect = eff.get("effect", "")
                break
        # Mechanics extras
        drain = None
        if meta.get("drain"):
            # PokeAPI uses signed int: positive heal percent of damage; convert to ratio
            # Common values: 50 -> 1/2, 75 -> 3/4
            val = meta.get("drain", 0)
            if val > 0:
                if val == 50: drain = [1,2]
                elif val == 75: drain = [3,4]
                else: drain = [val,100]
        recoil = None
        if meta.get("recoil"):
            rv = meta.get("recoil", 0)
            if rv > 0:
                if rv == 25: recoil = [1,4]
                elif rv == 33: recoil = [1,3]
                else: recoil = [rv,100]
        # Multi-hit
        min_hits = data.get("meta", {}).get("min_hits") or meta.get("min_hits")
        max_hits = data.get("meta", {}).get("max_hits") or meta.get("max_hits")
        multi_hit = [min_hits, max_hits] if (isinstance(min_hits,int) and isinstance(max_hits,int) and max_hits > 1) else None
        # Multi-turn (charging / binding)
        min_turns = meta.get("min_turns")
        max_turns = meta.get("max_turns")
        multi_turn = [min_turns, max_turns] if (isinstance(min_turns,int) and isinstance(max_turns,int) and max_turns > 1) else None
        flinch_chance = meta.get("flinch_chance", 0) or 0
        ailment = meta.get("ailment", {}).get("name") if isinstance(meta.get("ailment"), dict) else None
        ailment_chance = meta.get("ailment_chance", 0) or 0
        stat_changes: List[Dict[str, Any]] = []
        for sc in meta.get("stat_changes", []) or []:
            stat_changes.append({
                "stat": sc.get("stat", {}).get("name"),
                "change": sc.get("change"),
                "chance": meta.get("stat_chance", 0) or 0
            })
        # Flags (flag list provided in data["flags"] as names)
        flags_list = [f.get("name") for f in data.get("flags", []) if f.get("name")]
        def has(flag: str) -> bool: return flag in flags_list
        flags = {
            "contact": has("contact"),
            "sound": has("sound"),
            "punch": has("punch"),
            "bite": has("bite"),
            "powder": has("powder"),
            "pulse": has("pulse"),
            "ballistic": has("bullet"),
            "gravity": has("gravity"),
            "snatch": has("snatch"),
            "mirror": has("mirror"),
            "protect": has("protect"),
            "magic_coat": has("reflectable"),
            "defrost": has("defrost"),
            "charge": has("charge"),
        }
        move_obj = {
            "name": name,
            "display_name": _norm_display(name),
            "type": data.get("type", {}).get("name"),
            "category": dmg_class,
            "power": power,
            "accuracy": acc,
            "pp": pp,
            "priority": priority,
            "generation": gen_num,
            "crit_rate_stage": crit_stage,
            "targets": target,
            "short_effect": short_effect.strip(),
            "effect": full_effect.strip(),
            "drain": drain,
            "recoil": recoil,
            "multi_hit": multi_hit,
            "multi_turn": multi_turn,
            "flinch_chance": flinch_chance,
            "ailment": ailment,
            "ailment_chance": ailment_chance,
            "stat_changes": stat_changes,
            "flags": flags,
        }
        (MOVES / f"{name}.json").write_text(json.dumps(move_obj, indent=2))
        index.append(name)
    (MOVES / "moves_index.json").write_text(json.dumps(sorted(index), indent=2))
    print(f"Wrote {len(index)} moves (Gen I-IV) to {MOVES}")

if __name__ == "__main__":
    build_moves()
