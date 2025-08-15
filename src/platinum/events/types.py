from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
@dataclass
class Trigger:
    type: str
    location: str | None = None
    npc_id: str | None = None
    group_id: str | None = None
    map: str | None = None
    tile: tuple[int,int] | None = None
    name: str | None = None
    raw: Dict[str,Any] = field(default_factory=dict)
@dataclass
class ScriptCommand:
    cmd: str
    args: Dict[str, Any]
@dataclass
class EventDef:
    id: str
    category: str
    phase: int
    prerequisites: List[str]
    triggers: List[Trigger]
    script: List[ScriptCommand]
    once: bool = True
    set_flags: List[str] = field(default_factory=list)
    clear_flags: List[str] = field(default_factory=list)
    reward: Dict[str, Any] = field(default_factory=dict)
    next_hints: List[Dict[str, Any]] = field(default_factory=list)
