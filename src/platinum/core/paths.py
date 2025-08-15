from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # project root (assuming src/platinum/core/paths.py)
ASSETS = ROOT / "assets"
DIALOGUE_EN = ASSETS / "dialogue" / "en"
EVENTS = ASSETS / "events"
SCHEMA = ROOT / "schema"
SETTINGS_FILE_CANDIDATE_HOME = "~/.platinum_settings.json"