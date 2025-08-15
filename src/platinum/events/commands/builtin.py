from __future__ import annotations
from typing import Dict, Any
from platinum.events.commands.base import registry, ICommand
from platinum.core.logging import logger
from platinum.battle.models import make_pokemon

class ShowTextCommand:
    name = "SHOW_TEXT"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        key = action.get("dialogue_key")
        if key:
            ctx.dialogue.show(key)
        else:
            logger.warn("SHOW_TEXT missing dialogue_key")

class ShowDialogueCommand:
    name = "show_dialogue"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        key = action.get("dialogue_key")
        if key:
            ctx.dialogue.render(key)

class GiveItemCommand:
    name = "give_item"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        item = action.get("item")
        qty = int(action.get("quantity", 1))
        if item:
            ctx.add_item(item, qty)
            print(f"Received {qty} x {item}!")

class GivePokemonCommand:
    name = "give_pokemon"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        species = action.get("species")
        level = int(action.get("level", 5))
        if species:
            pk = make_pokemon(species, level)
            ctx.party.append(pk)
            print(f"{species.title()} joined your party!")

class StarterMenuCommand:
    name = "starter_menu"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        choices = ["turtwig","chimchar","piplup"]
        print("Choose your starter:")
        for i,s in enumerate(choices,1):
            print(f" {i}) {s.title()}")
        sel = None
        while sel not in range(1,4):
            try: sel = int(input("> "))
            except: pass
        species = choices[sel-1]
        pk = make_pokemon(species, 5)
        ctx.party.append(pk)
        print(f"{species.title()} joined your party!")
        ctx.set_flag("STARTER_CHOSEN")

# Placeholder trainer battle mapping
RIVAL_TEAMS = {
  "rival_intro": {"chimchar": [("piplup",5)], "piplup":[("turtwig",5)], "turtwig":[("chimchar",5)]}
}

class StartTrainerBattleCommand:
    name = "start_trainer_battle"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        battle_id = action.get("battle_id","unknown")
        # Determine rival starter advantage
        if battle_id.startswith("rival"):
            starter = None
            for p in ctx.party:
                if p.species in ("turtwig","chimchar","piplup"): starter = p.species; break
            team = RIVAL_TEAMS.get(battle_id, {}).get(starter or "turtwig", [("bidoof",5)])
            ctx.battle_service.start_trainer(battle_id, team)
        else:
            ctx.battle_service.start_trainer(battle_id, [("bidoof",5)])

class ScriptedCaptureDemoCommand:
    name = "scripted_capture_demo"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        print("(Dawn/Lucas demonstrates capturing a Bidoof...) (placeholder – no real capture)")
        ctx.set_flag("CATCH_TUTORIAL_DONE")

class SetLocationCommand:
    name = "set_location"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        loc = action.get("location")
        if loc and ctx.locations.exists(loc):
            ctx.player.location = loc
            print(f"Moved to {loc}")

class StartWildBattleCommand:
    name = "start_wild_battle"
    def execute(self, ctx, action: Dict[str, Any]) -> None:
        species = action.get("species", "bidoof")
        level = int(action.get("level", 5))
        ctx.battle_service.start_wild(species, level)

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
    commands = [
        ShowTextCommand(), ShowDialogueCommand(), GiveItemCommand(), GivePokemonCommand(),
        StarterMenuCommand(), StartTrainerBattleCommand(), ScriptedCaptureDemoCommand(),
        SetLocationCommand(), StartWildBattleCommand(), SetFlagCommand(), ClearFlagCommand(),
        StartBattleCommand()
    ]
    for cmd in commands:
        registry.register(cmd)

register_builtin()