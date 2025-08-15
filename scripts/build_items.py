"""Extract Gen I-IV relevant item data from PokeAPI raw dumps.

We keep: healing items, evolution stones/items, held battle items (berries, choice items,
leftovers, life-orb doesn't exist until Gen IV? (life-orb is Gen IV, keep), plates (introduced Gen IV),
stat boosting battle items (x-attack etc), and other core progression items (hm/tm are moves already handled).

Simplify for now: include ANY item whose generation <= 4 and has an English short effect.

Input: assets/pokemon/pokeapi_raw/pokeapi.co_api_v2_item_*.json
Output: assets/items/{slug}.json + items_index.json

Schema:
{
  "name": str,
  "display_name": str,
  "category": str,         # raw category name
  "cost": int|null,
  "fling_power": int|null,
  "effect": str,           # full English effect
  "short_effect": str,
  "generation": int,
  "is_consumable": bool,   # heuristic from category / effect text
  "attributes": [str, ...] # raw attribute slugs
}
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any

from platinum.core.paths import POKEMON_RAW, ITEMS

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

CONSUMABLE_KEYWORDS = {"restores","heals","restore","heal","cures","cure","pp"}


def _norm_display(name: str) -> str:
    return name.replace("-"," ").title()

def build_items():
    ITEMS.mkdir(parents=True, exist_ok=True)
    index: List[str] = []
    for p in sorted(POKEMON_RAW.glob("pokeapi.co_api_v2_item_*.json")):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        gen_name = None
        gi = data.get("game_indices")
        if isinstance(gi, list) and gi:
            gen_name = (gi[0].get("generation") or {}).get("name")
        if not gen_name:
            gen_name = (data.get("generation") or {}).get("name")
        if not gen_name:
            continue
        gen_num = GENERATION_NAME_TO_NUM.get(gen_name)
        if not gen_num or gen_num > 4:
            continue
        name = data.get("name")
        if not name:
            continue
        cost = data.get("cost")
        fling_power = (data.get("fling_power") if isinstance(data.get("fling_power"), int) else None)
        category = data.get("category", {}).get("name") or "unknown"
        attributes = [a.get("name") for a in data.get("attributes", []) if a.get("name")]
        effect = ""
        short_effect = ""
        for eff in data.get("effect_entries", []):
            if eff.get("language", {}).get("name") == "en":
                effect = eff.get("effect", "")
                short_effect = eff.get("short_effect", "")
                break
        # Basic consumable heuristic
        lowered = (short_effect or effect).lower()
        is_consumable = any(k in lowered for k in CONSUMABLE_KEYWORDS) or category in {"medicine","healing","vitamins","pp-recovery","status-cures","revival"}
        item_obj = {
            "name": name,
            "display_name": _norm_display(name),
            "category": category,
            "cost": cost,
            "fling_power": fling_power,
            "effect": effect.strip(),
            "short_effect": short_effect.strip(),
            "generation": gen_num,
            "is_consumable": bool(is_consumable),
            "attributes": attributes,
        }
        (ITEMS / f"{name}.json").write_text(json.dumps(item_obj, indent=2))
        index.append(name)
    (ITEMS / "items_index.json").write_text(json.dumps(sorted(index), indent=2))
    print(f"Wrote {len(index)} items (Gen I-IV) to {ITEMS}")

if __name__ == "__main__":
    build_items()
