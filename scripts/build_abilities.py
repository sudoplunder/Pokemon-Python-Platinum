"""Extract Gen I-IV ability data from PokeAPI raw dumps.

Input: assets/pokemon/pokeapi_raw/pokeapi.co_api_v2_ability_*.json
Output: assets/abilities/{ability_name}.json (slug)
         assets/abilities/abilities_index.json (list)

Captured fields:
{
  "name": str,            # slug
  "display_name": str,
  "generation": int,
  "short_effect": str,    # English short effect
  "effect": str,          # Full English effect
  "is_gen4_or_prior": bool
}

Only abilities whose originating generation <= 4 are written. (Gen IV introduced many new abilities, keep all <=4.)
Usage: python scripts/build_abilities.py
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any

from platinum.core.paths import POKEMON_RAW, ABILITIES

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

def _norm_display(name: str) -> str:
    return name.replace("-"," ").title()

def build_abilities():
    ABILITIES.mkdir(parents=True, exist_ok=True)
    index: List[str] = []
    for p in sorted(POKEMON_RAW.glob("pokeapi.co_api_v2_ability_*.json")):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        gen_name = data.get("generation", {}).get("name")
        if not gen_name:
            continue
        gen_num = GENERATION_NAME_TO_NUM.get(gen_name)
        if not gen_num or gen_num > 4:
            continue
        name = data.get("name")
        if not name:
            continue
        short_effect = ""
        long_effect = ""
        for eff in data.get("effect_entries", []):
            if eff.get("language", {}).get("name") == "en":
                long_effect = eff.get("effect", "")
                short_effect = eff.get("short_effect", "")
                break
        ability_obj = {
            "name": name,
            "display_name": _norm_display(name),
            "generation": gen_num,
            "short_effect": short_effect.strip(),
            "effect": long_effect.strip(),
            "is_gen4_or_prior": gen_num <= 4,
        }
        (ABILITIES / f"{name}.json").write_text(json.dumps(ability_obj, indent=2))
        index.append(name)
    (ABILITIES / "abilities_index.json").write_text(json.dumps(sorted(index), indent=2))
    print(f"Wrote {len(index)} abilities (Gen I-IV) to {ABILITIES}")

if __name__ == "__main__":
    build_abilities()
