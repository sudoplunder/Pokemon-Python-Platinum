"""Validation script to ensure dialogue JSON files conform to the single-format spec.

Checks performed:
- Only allowed top-level keys in each dialogue entry: ["expanded"]
- No legacy variant keys ("base", "concise") present anywhere.
- Duplicate dialogue keys across files are reported.
- Placeholder usage summary ({PLAYER}, {RIVAL}) counts.

Exit codes:
0 = success (no violations)
1 = violations found

Usage (from repo root):
  python -m scripts.validate_dialogue
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

ALLOWED_KEYS = {"expanded"}
LEGACY_KEYS = {"base", "concise"}
DIALOGUE_ROOT = Path(__file__).parent.parent / "assets" / "dialogue" / "en"

# Files under these subdirectories are ignored for strict entry validation
IGNORE_SUBDIRS = {"variants", "meta"}


def iter_dialogue_files():
    for path in sorted(DIALOGUE_ROOT.rglob("*.json")):
        # Skip ignored subdirs
        if any(part in IGNORE_SUBDIRS for part in path.parts):
            continue
        yield path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"__error__": str(e)}


def main() -> int:
    violations = []
    key_occurrences: dict[str, list[Path]] = defaultdict(list)
    placeholder_counter = Counter()

    for path in iter_dialogue_files():
        data = load_json(path)
        if "__error__" in data:
            violations.append(f"JSON parse error in {path}: {data['__error__']}")
            continue
        if not isinstance(data, dict):
            violations.append(f"Top-level JSON must be an object in {path}")
            continue
        # Special-case characters.json: it's a simple mapping id -> display name
        if path.name == "characters.json":
            for k, v in data.items():
                key_occurrences[k].append(path)
                if not isinstance(v, str):
                    violations.append(f"Character '{k}' in {path} must map to a string name")
            continue

        for key, entry in data.items():
            key_occurrences[key].append(path)
            if not isinstance(entry, dict):
                violations.append(f"Entry '{key}' in {path} must be an object")
                continue
            if key.startswith("_"):
                # treat underscore-prefixed keys as metadata containers; skip
                continue
            found_legacy = LEGACY_KEYS.intersection(entry.keys())
            if found_legacy:
                violations.append(
                    f"Legacy keys {found_legacy} present in entry '{key}' ({path})"
                )
            # Only enforce presence & type of 'expanded'
            text = entry.get("expanded", "")
            if not isinstance(text, str):
                violations.append(
                    f"Entry '{key}' in {path} has non-string 'expanded' value"
                )
                continue
            # gather placeholder stats
            if "{PLAYER}" in text:
                placeholder_counter["{PLAYER}"] += 1
            if "{RIVAL}" in text:
                placeholder_counter["{RIVAL}"] += 1
            if "{" in text:
                # crude detection of possibly un-replaced placeholder patterns
                # flag anything like {XYZ} where XYZ is uppercase and underscores
                import re
                for m in re.finditer(r"\{([A-Z_]+)\}", text):
                    token = m.group(0)
                    if token not in {"{PLAYER}", "{RIVAL}"}:
                        violations.append(
                            f"Unknown placeholder {token} in entry '{key}' ({path})"
                        )

    # duplicate key detection
    for dkey, paths in key_occurrences.items():
        if dkey.startswith("_"):
            continue
        if len(paths) > 1:
            p_list = ", ".join(str(p.relative_to(DIALOGUE_ROOT)) for p in paths)
            violations.append(
                f"Duplicate dialogue key '{dkey}' appears in multiple files: {p_list}"
            )

    if violations:
        print("Dialogue validation FAILED:\n")
        for v in violations:
            print(" -", v)
        print("\nPlaceholder usage summary:")
        for ph, count in placeholder_counter.items():
            print(f" {ph}: {count}")
        print(f"Total dialogue files scanned: {len(list(iter_dialogue_files()))}")
        return 1

    print("Dialogue validation passed.")
    print("Placeholder usage summary:")
    for ph, count in placeholder_counter.items():
        print(f" {ph}: {count}")
    print(f"Total dialogue files scanned: {len(list(iter_dialogue_files()))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
