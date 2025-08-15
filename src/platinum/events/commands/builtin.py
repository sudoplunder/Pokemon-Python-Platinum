from __future__ import annotations
from typing import Dict, Any
from platinum.events.commands.base import registry, ICommand
from platinum.core.logging import logger

class ShowTextCommand:
    name = "SHOW_TEXT"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        key = action.get("dialogue_key")
        if key:
            ctx.dialogue.show(key)
        else:
            logger.warn("SHOW_TEXT missing dialogue_key")

class SetFlagCommand:
    name = "SET_FLAG"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        f = action.get("flag")
        if f: ctx.set_flag(f)

class ClearFlagCommand:
    name = "CLEAR_FLAG"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        f = action.get("flag")
        if f: ctx.clear_flag(f)

class StartBattleCommand:
    name = "START_BATTLE"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        bid = action.get("battle_id","unknown")
        ctx.battle_service.start(bid)

def register_builtin():
    for cls in (ShowTextCommand, SetFlagCommand, ClearFlagCommand, StartBattleCommand):
        registry.register(cls())

register_builtin()