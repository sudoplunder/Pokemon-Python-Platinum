from __future__ import annotations
import os
from platinum.system.settings import Settings
from platinum.game.context import GameContext
from platinum.ui.menu import main_menu
from platinum.ui.opening import show_opening
from platinum.core.logging import logger

def _dev_loop(ctx: GameContext):
    """Developer debug command loop."""
    while True:
        cmd = input(":").strip()
        if cmd in ("exit","quit","q"): 
            break
        if cmd.startswith("/tp "):
            loc = cmd.split(" ",1)[1]
            ctx.set_flag(f"ENTERED_{loc.upper()}")
            ctx.player.location = loc
            print(f"Teleported to {loc}")
        elif cmd.startswith("/flag "):
            f = cmd.split(" ",1)[1]
            ctx.set_flag(f)
            print("Flag set")
        elif cmd.startswith("/encounter"):
            # simple route 204 south demo
            from platinum.battle.models import make_pokemon
            tbl = ctx.encounters.get("route_204_south_grass")
            if tbl: 
                species, lvl = tbl.choose(ctx.rng)
                ctx.battle_service.start_wild(species, lvl)
        elif cmd.startswith("/party"):
            for p in ctx.party:
                print(p.species, p.level, p.current_hp, "/", p.stats.hp)
        elif cmd.startswith("/give "):
            parts = cmd.split()
            if len(parts)>=2:
                item = parts[1]
                qty = int(parts[2]) if len(parts)>2 else 1
                ctx.add_item(item, qty)
                print("Gave", qty, item)
        else:
            print("Unknown dev cmd")

def _start_new_game(ctx: GameContext):
    print("\n== New Game ==\n")
    ctx.load_events()
    ctx.events.dispatch({"type":"game_start"})
    ctx.set_flag("OPENING_COMPLETE")

def run():
    settings = Settings.load()
    from platinum.core.logging import logger as global_logger
    global_logger.set_level(settings.data.log_level)
    ctx = GameContext(settings)
    show_opening()
    
    while True:
        has_save = ctx.save_store.exists()
        if has_save:
            choice = main_menu_with_continue()
        else:
            choice = main_menu()
            
        if choice == "new":
            _start_new_game(ctx)
        elif choice == "continue" and has_save:
            ctx.load()
            print("Game loaded!")
        elif choice == "options":
            settings.interactive_menu()
        elif choice == "flags":
            print("Flags:", ", ".join(ctx.debug_flags()) or "(none)")
        elif choice == "dev":
            _dev_loop(ctx)
        elif choice == "quit":
            print("Goodbye!")
            break
    settings.save()

def main_menu_with_continue():
    """Show main menu with continue option."""
    print("\n" + " " * 55 + "MAIN MENU")
    print("-" * 119)
    print("> Continue")
    print("  New Game")
    print("  Options")
    print("  View Flags (Debug)")
    print("  Developer Commands")
    print("  Quit")
    
    choice = input("\nSelect: ").strip().lower()
    mapping = {"1": "continue", "c": "continue", "continue": "continue",
               "2": "new", "n": "new", "new": "new",
               "3": "options", "o": "options", "options": "options",
               "4": "flags", "f": "flags", "flags": "flags",
               "5": "dev", "d": "dev", "dev": "dev",
               "6": "quit", "q": "quit", "quit": "quit"}
    return mapping.get(choice, "continue")