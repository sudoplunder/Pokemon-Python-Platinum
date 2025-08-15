import json, random
from pathlib import Path
from typing import Dict, Any
class DialogueManager:
    def __init__(self, lang_dir: str = "assets/dialogue/en", mode: str = "expanded"):
        self.lang_dir = Path(lang_dir)
        self.mode = mode
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()
        cfg_path = self.lang_dir / "variants" / "selector_config.json"
        self.selector_cfg = {}
        if cfg_path.exists():
            self.selector_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    def _load_all(self):
        for p in self.lang_dir.rglob("*.json"):
            if p.name in ("characters.json","selector_config.json"):
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            for key,val in data.items():
                if key.startswith("_"):
                    continue
                self._cache[key]=val
    def set_mode(self, mode: str):
        self.mode = mode
    def resolve(self, text_id: str) -> str:
        entry = self._cache.get(text_id)
        if not entry:
            return f"[missing:{text_id}]"
        target_mode = self.mode
        variant = None
        if target_mode in entry:
            variant = entry[target_mode]
        elif target_mode == "alt" and "alt" in entry:
            pool = entry["alt"]
            if isinstance(pool,list) and pool:
                variant = random.choice(pool)
        if variant is None:
            if "expanded" in entry: 
                variant = entry["expanded"]
            elif "base" in entry: 
                variant = entry["base"]
            else:
                alt = entry.get("alt")
                if isinstance(alt,list) and alt: 
                    variant = alt[0]
                else: 
                    variant = "[no text]"
        
        # Ensure we always return a string, not a list
        if isinstance(variant, list) and variant:
            variant = variant[0]
        elif isinstance(variant, list):
            variant = "[empty list]"
            
        return str(variant)
