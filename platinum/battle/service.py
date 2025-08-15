"""Battle service integrating improved core mechanics.

Provides a minimal loop that uses :mod:`platinum.battle.core` to resolve
placeholder encounters. Expandable to full party & AI later.
"""
from __future__ import annotations
from typing import Protocol, Literal, TypedDict, Dict, Any, Optional
from platinum.core.logging import logger
from platinum.system.settings import Settings
from .core import BattleCore, Battler, Move, FieldState
from platinum.data.loader import get_species
from .factory import battler_from_species
from .experience import clamp_level

class BattleResult(TypedDict):
    outcome: Literal["PLAYER_WIN","PLAYER_LOSS","ESCAPE","SCRIPTED"]
    battle_id: str

class IBattleService(Protocol):
    def start(self, battle_id: str) -> BattleResult: ...

class _DemoSpec(TypedDict):
    player: Dict[str, Any]
    enemy: Dict[str, Any]
    player_move: Move
    enemy_move: Move


_BATTLE_DEMOS: Dict[str, _DemoSpec] = {
    "tutorial_starly_1": _DemoSpec(
        player={"species": 387, "level": 5},   # Turtwig
        enemy={"species": 396, "level": 2},    # Starly
        player_move=Move(name="Tackle", type="normal", category="physical", power=40),
        enemy_move=Move(name="Tackle", type="normal", category="physical", power=40)
    )
}

class BattleService:
    def __init__(self):
        self.core = BattleCore()

    # Legacy/demo entry
    def start(self, battle_id: str) -> BattleResult:
        return self._run_demo(battle_id)

    def _run_demo(self, battle_id: str) -> BattleResult:
        # Always echo the battle id once so external tests (and players) can detect tutorial progression
        print(battle_id)
        if getattr(Settings.load().data, 'debug', False):
            logger.info("BattleStart", battle_id=battle_id)
        demo = _BATTLE_DEMOS.get(battle_id)
        if not demo:
            if getattr(Settings.load().data, 'debug', False):
                print(f"[BATTLE] (unimplemented) {battle_id} -> default win")
            return {"outcome": "PLAYER_WIN", "battle_id": battle_id}
        p_spec = demo["player"]
        e_spec = demo["enemy"]
        p = p_spec if isinstance(p_spec, Battler) else battler_from_species(p_spec["species"], p_spec["level"])
        e = e_spec if isinstance(e_spec, Battler) else battler_from_species(e_spec["species"], e_spec["level"], nickname="Wild " + get_species(e_spec["species"]) ["name"].capitalize())
        pm = demo.get("player_move") or (p.moves[0] if p.moves else Move(name="Struggle", type="normal", category="physical", power=50))  # type: ignore
        em = demo.get("enemy_move") or (e.moves[0] if e.moves else Move(name="Struggle", type="normal", category="physical", power=50))  # type: ignore
        return self._loop(p, e, pm, em, battle_id)

    def start_dynamic(self, *, enemy_species: int, enemy_level: int, player: Battler, battle_id: Optional[str]=None) -> BattleResult:
        """Run a dynamic single vs single battle using provided player battler.

        Returns BattleResult; outcome PLAYER_WIN if enemy faints else PLAYER_LOSS.
        """
        enemy_level = clamp_level(enemy_level)
        e = battler_from_species(enemy_species, enemy_level, nickname="Wild " + get_species(enemy_species)["name"].capitalize())
        # Pick first available move each turn (very naive AI)
        pm = player.moves[0] if player.moves else Move(name="Struggle", type="normal", category="physical", power=50)
        em = e.moves[0] if e.moves else Move(name="Struggle", type="normal", category="physical", power=50)
        bid = battle_id or f"wild_{enemy_species}_{enemy_level}"
        if getattr(Settings.load().data, 'debug', False):
            logger.info("BattleStartDynamic", battle_id=bid, enemy=enemy_species, level=enemy_level)
        return self._loop(player, e, pm, em, bid)

    def _loop(self, p: Battler, e: Battler, pm: Move, em: Move, battle_id: str) -> BattleResult:
        field = FieldState()
        turn = 1
        debug = getattr(Settings.load().data, 'debug', False)
        def _msg(s: str):
            if debug:
                print(f"[turn {turn}] {s}")
        # Attach temporary message callback
        saved_cb = self.core.message_cb
        self.core.message_cb = _msg
        try:
            while (p.current_hp and p.current_hp > 0 and e.current_hp and e.current_hp > 0):
                self.core.single_turn(p, pm, e, em, field)
                turn += 1
        finally:
            self.core.message_cb = saved_cb
        outcome = "PLAYER_WIN" if (p.current_hp and p.current_hp > 0) else "PLAYER_LOSS"
        return {"outcome": outcome, "battle_id": battle_id}

battle_service = BattleService()