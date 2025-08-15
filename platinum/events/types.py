from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Event:
    id: str
    trigger: Dict[str, Any]
    actions: List[Dict[str, Any]]
    once: bool = True
    set_flags: List[str] = field(default_factory=list)
    clear_flags: List[str] = field(default_factory=list)
    prerequisites: Dict[str, list] | None = None
    fired: bool = False

    def eligible(self, flags: set[str]) -> bool:
        if self.once and self.fired:
            return False
        if not self.prerequisites:
            return True
        all_req = self.prerequisites.get("all") or []
        any_req = self.prerequisites.get("any") or []
        none_req = self.prerequisites.get("none") or []
        if any_req and not any(r in flags for r in any_req):
            return False
        if all_req and not all(r in flags for r in all_req):
            return False
        if any(r in flags for r in none_req):
            return False
        return True