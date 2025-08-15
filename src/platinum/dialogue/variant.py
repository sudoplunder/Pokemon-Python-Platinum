from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List
import random

@dataclass
class DialogueEntry:
    key: str
    speaker: Optional[str]
    variants: Dict[str, str]  # base/concise/expanded etc.

class VariantSelector:
    def __init__(self, mode: str, rng: random.Random):
        self.mode = mode
        self.rng = rng

    def select(self, entry: DialogueEntry) -> str:
        if self.mode == "alt":
            pool: List[str] = []
            for k in ("expanded","base","concise"):
                v = entry.variants.get(k)
                if v:
                    pool.append(v)
            return self.rng.choice(pool) if pool else "<MISSING>"
        # fallback: mode -> base -> any
        return entry.variants.get(self.mode) or entry.variants.get("base") or next(iter(entry.variants.values()), "<MISSING>")