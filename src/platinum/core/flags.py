from __future__ import annotations
from typing import Set

class FlagSet:
    def __init__(self, event_engine):
        self._flags: Set[str] = set()
        self._engine = event_engine
    
    def set(self, flag: str, propagate: bool = True):
        if flag not in self._flags:
            self._flags.add(flag)
            if propagate:
                self._engine.on_flag_set(flag)
    
    def clear(self, flag: str):
        if flag in self._flags:
            self._flags.remove(flag)
    
    def has(self, flag: str) -> bool:
        return flag in self._flags
    
    def all(self):
        return sorted(self._flags)