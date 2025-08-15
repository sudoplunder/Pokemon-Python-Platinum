from __future__ import annotations
from typing import List
from .models import make_pokemon, Pokemon
from .mechanics import calculate_damage, accuracy_check
from .ai import choose_move
from .render import draw_hp_bar, format_battle_text
from ..core.logging import logger

class BattleService:
    def __init__(self, ctx):
        self.ctx = ctx
    
    def start_wild(self, species: str, level: int):
        wild = make_pokemon(species, level)
        if not self.ctx.party:
            logger.warn("NoPlayerPokemon")
            return
        print(f"A wild {species.title()} appeared! (Lv{level})")
        self._battle_loop(self.ctx.party[0], wild, wild=True)
    
    def start_trainer(self, battle_id: str, foe_team: List[tuple[str,int]]):
        foes = [make_pokemon(s,l) for s,l in foe_team]
        print(f"Trainer battle {battle_id} started!")
        self._battle_loop(self.ctx.party[0], foes[0], wild=False)
    
    def _battle_loop(self, player_mon: Pokemon, foe: Pokemon, wild: bool):
        rng = self.ctx.rng
        while not player_mon.is_fainted() and not foe.is_fainted():
            # Show HP bars
            player_bar = draw_hp_bar(player_mon.current_hp, player_mon.stats.hp)
            foe_bar = draw_hp_bar(foe.current_hp, foe.stats.hp)
            print(f"\n{player_mon.species.title()}: {player_bar} {player_mon.current_hp}/{player_mon.stats.hp}")
            print(f"{foe.species.title()}: {foe_bar} {foe.current_hp}/{foe.stats.hp}\n")
            
            pmove = choose_move(player_mon, foe)
            fmove = choose_move(foe, player_mon)
            # Speed simple: higher spe goes first; tie = player
            first_player = player_mon.stats.spe >= foe.stats.spe
            order = [(player_mon, foe, pmove)] if first_player else [(foe, player_mon, fmove)]
            order.append((foe, player_mon, fmove) if first_player else (player_mon, foe, pmove))
            
            for atk, tgt, mv in order:
                if atk.is_fainted() or tgt.is_fainted():
                    continue
                if not accuracy_check(mv, rng):
                    print(format_battle_text(f"{atk.species.title()} used {mv.id.title()}... missed!"))
                    continue
                dmg, meta = calculate_damage(atk, tgt, mv, rng)
                tgt.current_hp = max(0, tgt.current_hp - dmg)
                crit_txt = " CRITICAL!" if meta["crit"] else ""
                print(format_battle_text(f"{atk.species.title()} used {mv.id.title()}! {dmg} dmg.{crit_txt}"))
                if tgt.is_fainted():
                    print(format_battle_text(f"{tgt.species.title()} fainted!"))
                    break
        
        if foe.is_fainted():
            print(format_battle_text("You won the battle! (XP gain TODO)"))
        else:
            print(format_battle_text("You blacked out... (placeholder)"))

# Legacy stub for compatibility
class StubBattleService:
    def start(self, battle_id: str) -> None:
        logger.info("Battle (stub)", battle_id=battle_id)
        print(f"[BATTLE] (stub) {battle_id}: PLAYER_WIN")

battle_service = StubBattleService()