from __future__ import annotations
from typing import Protocol
from platinum.core.logging import logger

class IBattleService(Protocol):
    def start(self, battle_id: str) -> None: ...

class StubBattleService:
    def start(self, battle_id: str) -> None:
        logger.info("Battle (stub)", battle_id=battle_id)
        print(f"[BATTLE] (stub) {battle_id}: PLAYER_WIN")

battle_service = StubBattleService()