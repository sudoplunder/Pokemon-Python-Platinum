"""Build normalized per-species JSON files (Gen I-IV) from raw PokeAPI dumps.

Input directory: assets/pokemon/pokeapi_raw (pre-fetched endpoint JSONs)
Outputs: assets/pokemon/species/{dex:03}.json (one per National Dex <= 493)

We intentionally scope to:
- Core species (no forms / mega / regional variants beyond Gen IV)
- Fields required by early battle + party systems.

Schema (per file):
{
  "id": int,                  # National Dex id
  "name": str,                # canonical species slug
  "generation": int,          # 1-4
    "types": [str, ...],        # 1 or 2, lowercase (fairy removed; original fairy species downgraded to pre-fairy Gen IV types)
  "base_stats": {             # raw base stats
      "hp": int, "attack": int, "defense": int,
      "sp_atk": int, "sp_def": int, "speed": int
  },
  "base_experience": int,
  "growth_rate": str,         # as named by API
  "capture_rate": int,
  "gender_rate": int,         # -1 genderless else 0-8 female ratio steps
  "hatch_cycles": int,
  "base_friendship": int,
  "egg_groups": [str, ...],
  "abilities": {              # slots (1,2,hidden?)
      "primary": str,
      "secondary": str | null,
      "hidden": str | null
  },
  "moves": {                  # learnsets (level + machines)
      "level_up": [ {"level": int, "name": str} ],
      "machines": [str, ...]   # TM/HM move names (Gen IV relevant)
  },
  "evolution": {              # minimal forward evolution info from chain
      "evolves_to": [
         {"id": int, "trigger": str, "conditions": {k: v}}
      ]
  }
}

Execution adds a summary index file species_index.json with array of ids for quick scanning.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List

from platinum.core.paths import POKEMON, POKEMON_RAW

DEX_LIMIT = 493
OUT_DIR = POKEMON / "species"

# Regex helpers to map raw filenames to ids
POKEMON_FILE = re.compile(r"pokemon_(\d+)_")
SPECIES_FILE = re.compile(r"pokemon-species_(\d+)_")

# Preload raw JSON blobs keyed by id

def _load_index(prefix: str, rx: re.Pattern[str]) -> Dict[int, Path]:
    paths: Dict[int, Path] = {}
    for p in POKEMON_RAW.glob(f"pokeapi.co_api_v2_{prefix}_*.json"):
        m = rx.search(p.name)
        if not m:
            continue
        i = int(m.group(1))
        if i <= DEX_LIMIT:
            paths[i] = p
    return paths

pokemon_paths = _load_index("pokemon", POKEMON_FILE)
species_paths = _load_index("pokemon-species", SPECIES_FILE)

###########################
# Generation / version groups
###########################

# Version group -> generation (only needed if later expansion)
VERSION_GROUP_GEN = {
    1: 1, 2: 1, 3: 1,   # red/blue/yellow
    4: 2, 5: 2, 6: 2,   # gold/silver/crystal
    7: 3, 8: 3, 9: 3,   # ruby/sapphire/emerald
    10: 3, 11: 3,       # firered/leafgreen
    12: 4, 13: 4, 14: 4 # diamond/pearl/platinum
}

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

###########################
# Ability generation pruning (hidden abilities added later)
###########################

ABILITY_GEN: Dict[str, int] = {}
for ability_file in POKEMON_RAW.glob("pokeapi.co_api_v2_ability_*.json"):
    try:
        data = json.loads(ability_file.read_text())
    except Exception:
        continue
    gen_name = data.get("generation", {}).get("name")
    if not gen_name:
        continue
    gen_num = GENERATION_NAME_TO_NUM.get(gen_name)
    if not gen_num:
        continue
    name = data.get("name")
    if name:
        ABILITY_GEN[name] = gen_num

# We only want level-up moves that are learned in any gen 4 version group.
# Use only Diamond / Pearl / Platinum version groups (12,13,14) for Gen IV learn data
GEN4_LEVEL_VG_IDS = {12, 13, 14}
GEN4_MACHINE_VG_IDS = {12, 13, 14}
GEN4_MACHINE_METHODS = {"machine"}

###########################
# Move generation pruning
###########################

def _scan_moves() -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for move_file in POKEMON_RAW.glob("pokeapi.co_api_v2_move_*.json"):
        try:
            data = json.loads(move_file.read_text())
        except Exception:
            continue
        gen_name = data.get("generation", {}).get("name")
        if not gen_name:
            continue
        gen_num = GENERATION_NAME_TO_NUM.get(gen_name)
        if not gen_num:
            continue
        move_name = data.get("name")
        if move_name:
            mapping[move_name] = gen_num
    return mapping

move_generation = _scan_moves()

def _scan_allowed_machines() -> set[str]:
    allowed: set[str] = set()
    # Machine JSON files include version_group, move
    for machine_file in POKEMON_RAW.glob("pokeapi.co_api_v2_machine_*.json"):
        try:
            data = json.loads(machine_file.read_text())
        except Exception:
            continue
        vg = data.get("version_group", {}).get("url", "").rstrip("/").split("/")[-1]
        try:
            vg_id = int(vg)
        except ValueError:
            continue
        if vg_id not in GEN4_MACHINE_VG_IDS:
            continue
        move = data.get("move", {}).get("name")
        if not move:
            continue
        # Skip post-Gen IV moves
        if move_generation.get(move, 999) > 4:
            continue
        allowed.add(move)
    return allowed

ALLOWED_GEN4_MACHINES = _scan_allowed_machines()

# Evolution chain regex (future use if raw chain data is later added)
EV_CHAIN_RX = re.compile(r"evolution-chain/(\d+)/")

# Evolution chain files might not be downloaded; we derive forward evolution minimal info from species entries only.
# Simpler: build adjacency from species.evolves_from_species.
parent_map: Dict[int, str] = {}
children_map: Dict[int, List[int]] = defaultdict(list)
for sid, sp_path in species_paths.items():
    data = json.loads(sp_path.read_text())
    if data.get("evolves_from_species"):
        parent_name = data["evolves_from_species"]["name"]
        # Find parent id via name -> id lookup later; temporarily store name
        parent_map[sid] = parent_name  # type: ignore

# Build name->id mapping from species names
name_to_id: Dict[str, int] = {}
for sid, sp_path in species_paths.items():
    data = json.loads(sp_path.read_text())
    name_to_id[data["name"]] = sid

resolved_parent: Dict[int, int] = {}
for child_id, parent_name in parent_map.items():
    pid = name_to_id.get(parent_name)  # resolve by name
    if pid is not None:
        resolved_parent[child_id] = pid
        children_map[pid].append(child_id)

###########################
# Evolution overrides (to supply conditions while raw chain data absent)
###########################

_EVOLUTION_OVERRIDES_PATH = POKEMON / "evolution_overrides.json"
if _EVOLUTION_OVERRIDES_PATH.exists():
    try:
        _EVOLUTION_OVERRIDES = json.loads(_EVOLUTION_OVERRIDES_PATH.read_text())
    except Exception:
        _EVOLUTION_OVERRIDES = {}
else:
    _EVOLUTION_OVERRIDES = {}

def build_evolution_info(species_id: int) -> Dict[str, Any]:
    return {
        "evolves_to": [
            {"id": cid, "trigger": "level-up", "conditions": {}} for cid in sorted(children_map.get(species_id, []))
        ]
    }

STAT_KEY_MAP = {"hp": "hp", "attack": "attack", "defense": "defense", "special-attack": "sp_atk", "special-defense": "sp_def", "speed": "speed"}

def extract_moves(pokemon: Dict[str, Any]) -> Dict[str, Any]:
    """Return Gen IV legal moves for the species.

    We already constrain by version groups (12/13/14). Additionally prune any move
    whose originating generation is > 4 (e.g. Hurricane, Scald, etc.).
    """
    level: List[Dict[str, Any]] = []
    machines: set[str] = set()
    for m in pokemon.get("moves", []):
        name = m["move"]["name"]
        # Skip moves introduced after Gen IV entirely
        if move_generation.get(name, 999) > 4:
            continue
        min_level = None
        machine_here = False
        for ver in m.get("version_group_details", []):
            vg_id = ver["version_group"]["url"].rstrip("/").split("/")[-1]
            try:
                vg = int(vg_id)
            except ValueError:
                continue
            if vg in GEN4_LEVEL_VG_IDS or vg in GEN4_MACHINE_VG_IDS:
                method = ver["move_learn_method"]["name"]
                if method == "level-up" and vg in GEN4_LEVEL_VG_IDS:
                    lvl = ver["level_learned_at"]
                    if lvl == 0:
                        continue
                    if min_level is None or lvl < min_level:
                        min_level = lvl
                elif method in GEN4_MACHINE_METHODS and vg in GEN4_MACHINE_VG_IDS:
                    machine_here = True
        if min_level is not None:
            level.append({"level": min_level, "name": name})
        if machine_here and name in ALLOWED_GEN4_MACHINES:
            machines.add(name)
    level.sort(key=lambda x: (x["level"], x["name"]))
    return {"level_up": level, "machines": sorted(machines)}


def normalize_species(species_id: int, pokemon_path: Path, species_path: Path) -> Dict[str, Any]:
    p = json.loads(pokemon_path.read_text())
    s = json.loads(species_path.read_text())

    types = [t["type"]["name"] for t in sorted(p["types"], key=lambda x: x["slot"])]
    # Remove fairy (not present in Gen IV)
    types = [t for t in types if t != "fairy"]
    # Fallback original Normal typing for species that become empty due to retcon
    if not types:
        if s["name"] in {"cleffa", "clefairy", "clefable", "snubbull", "granbull", "togepi"}:
            types = ["normal"]
    stats: Dict[str, int] = {}
    for stat in p["stats"]:
        stat_name = STAT_KEY_MAP[stat["stat"]["name"]]
        stats[stat_name] = stat["base_stat"]

    abilities_sorted = sorted(p["abilities"], key=lambda a: a["slot"])  # slot 1 primary, slot 2 secondary, hidden flagged
    primary = None
    secondary = None
    hidden = None
    for a in abilities_sorted:
        if a["is_hidden"]:
            hidden = a["ability"]["name"]
        elif a["slot"] == 1:
            primary = a["ability"]["name"]
        elif a["slot"] == 2:
            secondary = a["ability"]["name"]
    # Prune hidden ability if introduced after Gen 4
    if hidden and ABILITY_GEN.get(hidden, 999) > 4:
        hidden = None
    moves = extract_moves(p)

    # Build richer evolution structure
    parent_id = resolved_parent.get(species_id)
    forward = sorted(children_map.get(species_id, []))
    evo = {
        "previous": parent_id,
        "next": forward,
        "root": (lambda x: x if resolved_parent.get(x) is None else None)(species_id),
        "next_details": []
    }
    # root flag fix
    if evo["root"] is None:
        # find root by climbing parents
        r = species_id
        while resolved_parent.get(r):
            r = resolved_parent[r]
        evo["root"] = r

    # Apply overrides if present for this species to populate next_details
    overrides = _EVOLUTION_OVERRIDES.get(str(species_id)) or []
    # Filter to only forward ids that truly are children
    detailed = []
    for entry in overrides:
        tid = entry.get("id")
        if tid in forward:
            detailed.append({
                "id": tid,
                "trigger": entry.get("trigger", "level-up"),
                "conditions": entry.get("conditions", {})
            })
    if detailed:
        evo["next_details"] = detailed

    normalized = {
        "id": species_id,
        "name": p["name"],
        "generation": s["generation"]["url"].rstrip("/").split("/")[-1] if s.get("generation") else None,
        "types": types,
        "base_stats": stats,
        "base_experience": p.get("base_experience"),
        "growth_rate": s.get("growth_rate", {}).get("name"),
        "capture_rate": s.get("capture_rate"),
        "gender_rate": s.get("gender_rate"),
        "hatch_cycles": s.get("hatch_counter"),
        "base_friendship": s.get("base_happiness"),
        "egg_groups": [eg["name"] for eg in s.get("egg_groups", [])],
    "abilities": {"primary": primary, "secondary": secondary, "hidden": hidden},
    "moves": moves,
    "evolution": evo
    }
    return normalized


def build_all():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    for i in sorted(pokemon_paths.keys()):
        if i not in species_paths:
            continue
        data = normalize_species(i, pokemon_paths[i], species_paths[i])
        # Skip if generation > 4
        try:
            gen = int(data["generation"]) if data["generation"] else 0
        except ValueError:
            gen = 0
        if gen and gen > 4:
            continue
        out_path = OUT_DIR / f"{i:03}.json"
        out_path.write_text(json.dumps(data, indent=2))
        index.append(i)
    (POKEMON / "species_index.json").write_text(json.dumps(index, indent=2))
    print(f"Wrote {len(index)} species (<= Gen IV) to {OUT_DIR}")

if __name__ == "__main__":
    build_all()
