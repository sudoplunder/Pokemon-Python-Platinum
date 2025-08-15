"""Build Gen IV TM/HM mapping.

Derives machine (TM/HM) -> move mapping for Diamond/Pearl/Platinum (version groups 12,13,14)
using raw machine endpoint dumps plus filtered move generation (<= Gen IV).

Output:
  assets/machines/machines_gen4.json
  Schema:
  {
     "tm": { "TM01": {"move": "focus-punch", "type": "fighting", "category": "physical|special|status", "power": int|null, "accuracy": int|null }, ... },
     "hm": { "HM01": { ... } }
  }

We map machine item names (e.g., tm01) to canonical upper-case codes TM01 / HM02.
If multiple version groups supply same numbering, last write wins (they should be consistent across D/P/Pt for Gen IV moves kept).
"""
from __future__ import annotations
import json, re
from typing import Dict, Any
from platinum.core.paths import POKEMON_RAW, MOVES, MACHINES

GEN4_VG = {12,13,14}
MOVE_CACHE: Dict[str, Dict[str, Any]] = {}

MOVE_FILE_RX = re.compile(r"pokeapi.co_api_v2_move_(.+)\.json$")

# Load move details (already filtered for <= Gen IV when using build_moves; here we trust and just read if exists)

def _load_move(name: str) -> Dict[str, Any]:
    if name in MOVE_CACHE: return MOVE_CACHE[name]
    path = MOVES / f"{name}.json"
    if not path.exists():
        return {}
    MOVE_CACHE[name] = json.loads(path.read_text())
    return MOVE_CACHE[name]

MACHINE_CODE_RX = re.compile(r"^(tm|hm)(\d+)$")

def build_machines():
    MACHINES.mkdir(parents=True, exist_ok=True)
    tm_map: Dict[str, Any] = {}
    hm_map: Dict[str, Any] = {}
    for mf in sorted(POKEMON_RAW.glob("pokeapi.co_api_v2_machine_*.json")):
        try:
            data = json.loads(mf.read_text())
        except Exception:
            continue
        vg_url = data.get("version_group", {}).get("url", "")
        vg_id = vg_url.rstrip("/").split("/")[-1]
        try:
            vg = int(vg_id)
        except ValueError:
            continue
        if vg not in GEN4_VG:
            continue
        move_name = data.get("move", {}).get("name")
        item_name = data.get("item", {}).get("name")
        if not move_name or not item_name: continue
        m = MACHINE_CODE_RX.match(item_name)
        if not m: continue
        prefix, num = m.group(1).upper(), int(m.group(2))
        code = f"{prefix}{num:02d}"
        move_obj = _load_move(move_name)
        if not move_obj:  # skip moves we didn't include (post Gen IV)
            continue
        entry = {
            "move": move_name,
            "type": move_obj.get("type"),
            "category": move_obj.get("category"),
            "power": move_obj.get("power"),
            "accuracy": move_obj.get("accuracy"),
        }
        if prefix == "TM":
            tm_map[code] = entry
        else:
            hm_map[code] = entry
    out = {"tm": dict(sorted(tm_map.items())), "hm": dict(sorted(hm_map.items()))}
    (MACHINES / "machines_gen4.json").write_text(json.dumps(out, indent=2))
    print(f"Wrote {len(tm_map)} TMs and {len(hm_map)} HMs to {MACHINES / 'machines_gen4.json'}")

if __name__ == "__main__":
    build_machines()
