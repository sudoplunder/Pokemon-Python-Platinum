"""Higher-level battle session orchestration for 1v1 party-based battles.

Incremental scaffold atop BattleCore mechanics.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random
from .core import BattleCore, Battler, Move, FieldState
from .capture import attempt_capture, flee_success
from platinum.data.loader import get_species
from platinum.encounters.loader import roll_encounter, EncounterMethod

@dataclass
class Party:
    members: List[Battler]
    active_index: int = 0

    def active(self) -> Battler:
        return self.members[self.active_index]

    def has_available(self) -> bool:
        return any((m.current_hp or 0) > 0 for m in self.members)

    def auto_switch_if_fainted(self) -> Optional[Battler]:
        if (self.active().current_hp or 0) > 0:
            return None
        for i, m in enumerate(self.members):
            if (m.current_hp or 0) > 0:
                self.active_index = i
                return m
        return None

class BattleSession:
    def __init__(self, player: Party, enemy: Party, core: Optional[BattleCore] = None, *, is_wild: bool = True):
        self.player = player
        self.enemy = enemy
        self.core = core or BattleCore()
        self.field = FieldState()
        self.turn_counter = 0
        self.log: List[str] = []
        self.is_wild = is_wild

        def _capture(msg: str):
            self.log.append(msg)
        self.core.message_cb = _capture

    def is_over(self) -> bool:
        return (not self.player.has_available()) or (not self.enemy.has_available())

    def step(self, player_move_idx: int = 0, enemy_move_idx: int = 0):
        self.player.auto_switch_if_fainted()
        self.enemy.auto_switch_if_fainted()
        if self.is_over():
            return
        p_act = self.player.active()
        e_act = self.enemy.active()
        # Determine if Struggle is required (no usable PP on any move)
        def choose_move(b: Battler, idx: int) -> Move:
            if not b.moves:
                return Move(name="Struggle", type="normal", category="physical", power=50, recoil_ratio=(1,4))
            if all((m.max_pp > 0 and m.pp <= 0) for m in b.moves):
                return Move(name="Struggle", type="normal", category="physical", power=50, recoil_ratio=(1,4))
            # Clamp index and skip to first move with PP if selected depleted
            if idx >= len(b.moves):
                idx = 0
            chosen = b.moves[idx]
            if chosen.max_pp > 0 and chosen.pp <= 0:
                for m in b.moves:
                    if m.max_pp > 0 and m.pp > 0:
                        return m
                return Move(name="Struggle", type="normal", category="physical", power=50, recoil_ratio=(1,4))
            return chosen
        p_move = choose_move(p_act, player_move_idx)
        e_move = choose_move(e_act, enemy_move_idx)
        self.core.single_turn(p_act, p_move, e_act, e_move, self.field)
        self.turn_counter += 1

    def run_auto(self, max_turns: int = 200):
        while not self.is_over() and self.turn_counter < max_turns:
            self.step()
        return self.outcome()

    def outcome(self) -> str:
        if self.player.has_available() and not self.enemy.has_available():
            return "PLAYER_WIN"
        if self.enemy.has_available() and not self.player.has_available():
            return "PLAYER_LOSS"
        if self.turn_counter >= 200:
            return "STALEMATE"
        return "ONGOING"

    # ---------------- Capturing & Fleeing (wild only assumptions) -----------------
    def attempt_capture(self, ball: str = 'poke-ball') -> str:
        if not self.is_wild:
            return 'NOT_ALLOWED'
        enemy_active = self.enemy.active()
        # Real capture_rate from species data using stored species_id
        capture_rate = 45
        try:
            sp = get_species(enemy_active.species_id)
            if isinstance(sp, dict):
                capture_rate = int(sp.get("capture_rate", capture_rate))
        except Exception:
            pass
        max_hp = enemy_active.stats['hp']
        cur_hp = enemy_active.current_hp or max_hp
        # Quick Ball only applies full modifier on very first turn (turn_counter == 0)
        if ball == 'quick-ball' and self.turn_counter > 0:
            ball = 'poke-ball'
        res = attempt_capture(self.core.rng, capture_rate, max_hp, cur_hp, ball, enemy_active.status)
        if res.success:
            return 'CAPTURED'
        return f'BREAK_OUT_{res.shakes}'

    def attempt_flee(self, attempts: int = 1) -> bool:
        p = self.player.active()
        e = self.enemy.active()
        return flee_success(self.core.rng, p.stats['speed'], e.stats['speed'], attempts)

    @classmethod
    def from_wild_encounter(cls, player_party: Party, zone: str, method: EncounterMethod, level: int | None = None, rng: Optional[random.Random] = None) -> 'BattleSession':
        """Factory: generate a wild encounter based on encounter tables.

        If level is None we roll; otherwise use provided level.
        """
        rng = rng or random.Random()
        if level is None:
            res = roll_encounter(zone, method, rng=rng)
            if not res:
                raise ValueError(f"No encounter available for zone={zone} method={method}")
            species_id, level = res
        else:
            res = roll_encounter(zone, method, rng=rng)
            if not res:
                raise ValueError(f"No encounter available for zone={zone} method={method}")
            species_id, _ = res
        from .factory import battler_from_species
        wild = battler_from_species(species_id, level)
        enemy_party = Party([wild])
        return cls(player_party, enemy_party, is_wild=True)

__all__ = ["BattleSession","Party"]
