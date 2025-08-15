"""
Stub battle service so START_BATTLE event commands can call into a unified interface.

Replace / extend this with a full Gen IV mechanics implementation later.
"""
from __future__ import annotations
from typing import Protocol, Literal, TypedDict
from platinum.core.logging import logger

class BattleResult(TypedDict):
    outcome: Literal["PLAYER_WIN","PLAYER_LOSS","ESCAPE","SCRIPTED"]
    battle_id: str

class IBattleService(Protocol):
    def start(self, battle_id: str) -> BattleResult: ...

class StubBattleService:
    def start(self, battle_id: str) -> BattleResult:
        logger.info("BattleStubStart", battle_id=battle_id)
        # Placeholder display (could later hook into a richer renderer)
        print(f"[BATTLE] (stub) {battle_id}")
        print("[BATTLE] (stub) Result: PLAYER_WIN")
        return {"outcome": "PLAYER_WIN", "battle_id": battle_id}

battle_service = StubBattleService()