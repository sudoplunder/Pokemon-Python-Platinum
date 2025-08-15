from __future__ import annotations
from typing import Any
from platinum.system.save import PartyMember
from platinum.battle.experience import clamp_level
from platinum.ui.menu_nav import select_menu

"""Event script command handlers (with arrow/W/S starter selection)."""

_STARTERS: dict[int, str] = {387: "turtwig", 390: "chimchar", 393: "piplup"}
_RIVAL_COUNTER: dict[int, int] = {387: 390, 390: 393, 393: 387}

def handle_show_text(ctx, action: dict):
    key = action.get("dialogue_key")
    if key:
        ctx.dialogue.show(key)

def handle_set_flag(ctx, action: dict):
    flag = action.get("flag")
    if flag:
        ctx.set_flag(flag)

def handle_clear_flag(ctx, action: dict):
    flag = action.get("flag")
    if flag:
        ctx.clear_flag(flag)

def handle_start_battle(ctx, action: dict):
    # Dynamic single battle: expects enemy_species (either numeric id or name) & level
    bid = action.get("battle_id", "unknown")
    # Echo battle id so tests can assert progression even with debug off
    if bid:
        print(bid)
    enemy_species = action.get("enemy_species") or action.get("species")
    enemy_level = int(action.get("enemy_level", action.get("level", 3)))
    interactive = bool(action.get("interactive"))
    # Special case: first rival battle should use rival's starter (type advantage) if not explicitly specified
    if bid == "tutorial_starly_1" and enemy_species is None:
        # Determine player's starter species id (we stored string names like 'turtwig')
        if ctx.state.party:
            from platinum.data.species_lookup import species_id as _sid
            try:
                player_sid = _sid(ctx.state.party[0].species)
                rival_sid = _RIVAL_COUNTER.get(player_sid)
                if rival_sid:
                    enemy_species = rival_sid
                    enemy_level = max(enemy_level, ctx.state.party[0].level)
            except Exception:
                pass
    if not ctx.state.party:
        print("[battle] Skipped: player has no party")
        return
    if interactive:
        from platinum.battle.factory import battler_from_species
        from platinum.data.species_lookup import species_id
        from platinum.ui.battle import run_battle_ui
        from platinum.battle.session import Party, BattleSession
        from platinum.battle.experience import exp_gain, apply_experience

        player_battlers: list[Any] = []
        for pm in ctx.state.party:
            try:
                sid = species_id(pm.species) if isinstance(pm.species, str) else int(pm.species)
            except Exception:
                continue
            player_battlers.append(battler_from_species(sid, pm.level, nickname=pm.species.capitalize()))
        # Inject badge count for obedience mechanic
        badge_count = len(getattr(ctx.state, 'badges', []))
        for b in player_battlers:
            setattr(b, 'badge_count', badge_count)

        enemy_battlers: list[Any] = []
        if enemy_species is not None:
            try:
                e_sid = species_id(enemy_species) if isinstance(enemy_species, str) else int(enemy_species)
            except Exception:
                enemy_battlers = []
            else:
                enemy_battlers.append(battler_from_species(e_sid, enemy_level, nickname=str(enemy_species).capitalize()))

        # Fallback to legacy scripted battle if enemy couldn't be built dynamically
        if not enemy_battlers:
            res = ctx.battle_service.start(bid)
            if getattr(ctx.settings.data, 'debug', False):
                print(f"[battle] Result: {res['outcome']}")
            if res['outcome'] == 'PLAYER_WIN':
                ctx.set_flag(f"battle_{bid}_won")
            else:
                ctx.set_flag(f"battle_{bid}_lost")
            return

        session = BattleSession(Party(player_battlers), Party(enemy_battlers), is_wild=not action.get("trainer"))
        if getattr(ctx.settings.data, 'debug', False):
            print(f"[battle] (interactive) {bid}")
        outcome = run_battle_ui(session, is_trainer=bool(action.get("trainer")))
        if outcome == 'PLAYER_WIN':
            ctx.set_flag(f"battle_{bid}_won")
            if enemy_battlers:
                e_b = enemy_battlers[0]
                g = exp_gain(e_b.species_id, e_b.level, is_trainer=bool(action.get("trainer")))
                pm = ctx.state.party[0]
                from platinum.data.species_lookup import species_id as _sid_for
                try:
                    pm_sid = _sid_for(pm.species) if isinstance(pm.species, str) else int(pm.species)
                except Exception:
                    pm_sid = None
                res = apply_experience(pm, g, species_id=pm_sid)
                if getattr(ctx.settings.data, 'debug', False):
                    msg = f"{pm.species.capitalize()} gained {g} EXP!"
                    if res['leveled']:
                        msg += f" Grew to Lv{pm.level}!"
                        if res.get('learned'):
                            learned_str = ", ".join(m.title() for m in res['learned'])
                            msg += f" Learned {learned_str}!"
                    print(msg)
        elif outcome == 'PLAYER_LOSS':
            ctx.set_flag(f"battle_{bid}_lost")
        elif outcome == 'ESCAPE':
            ctx.set_flag(f"battle_{bid}_escape")
        return
    # Non-interactive path
    player_member = ctx.state.party[0]
    from platinum.battle.factory import battler_from_species
    from platinum.data.species_lookup import species_id
    try:
        p_species_id = species_id(player_member.species) if isinstance(player_member.species, str) else int(player_member.species)
    except Exception:
        print(f"[battle] Invalid player species {player_member.species}")
        return
    player_battler = battler_from_species(p_species_id, player_member.level, nickname=str(player_member.species).capitalize())
    if enemy_species is None:
        result = ctx.battle_service.start(bid)
    else:
        try:
            e_sid = species_id(enemy_species) if isinstance(enemy_species, str) else int(enemy_species)
        except Exception:
            print(f"[battle] Invalid enemy species {enemy_species}; using demo")
            result = ctx.battle_service.start(bid)
        else:
            result = ctx.battle_service.start_dynamic(enemy_species=e_sid, enemy_level=enemy_level, player=player_battler, battle_id=bid)
    if getattr(ctx.settings.data, 'debug', False):
        print(f"[battle] Result: {result['outcome']}")
    if result['outcome'] == 'PLAYER_WIN':
        ctx.set_flag(f"battle_{bid}_won")
        # Rough EXP award (auto path). If dynamic enemy used we have species id; else skip.
        if enemy_species is not None:
            from platinum.battle.experience import exp_gain, apply_experience
            from platinum.data.species_lookup import species_id as _sid
            try:
                e_sid2 = enemy_species if isinstance(enemy_species, int) else _sid(enemy_species)
                g = exp_gain(e_sid2, enemy_level, is_trainer=bool(action.get("trainer")))
                pm = ctx.state.party[0]
                from platinum.data.species_lookup import species_id as _sid_for2
                try:
                    pm_sid = _sid_for2(pm.species) if isinstance(pm.species, str) else int(pm.species)
                except Exception:
                    pm_sid = None
                res = apply_experience(pm, g, species_id=pm_sid)
                if getattr(ctx.settings.data, 'debug', False):
                    msg = f"{pm.species.capitalize()} gained {g} EXP!"
                    if res['leveled']:
                        msg += f" Grew to Lv{pm.level}!"
                        if res.get('learned'):
                            learned_str = ", ".join(m.title() for m in res['learned'])
                            msg += f" Learned {learned_str}!"
                    print(msg)
            except Exception:
                pass
    else:
        ctx.set_flag(f"battle_{bid}_lost")

def handle_set_location(ctx, action: dict):
    loc = action.get("location")
    if loc:
        if hasattr(ctx, "set_location"):
            ctx.set_location(loc)
        else:
            ctx.state.location = loc

def handle_add_party(ctx, action: dict):
    species = action.get("species")
    level = clamp_level(int(action.get("level", 5)))
    if species:
        ctx.state.party.append(PartyMember(species=species, level=level, hp=20, max_hp=20))
        if ctx.settings.data.autosave and hasattr(ctx, "_autosave"):
            ctx._autosave()

def handle_choose_starter(ctx, action: dict):
    if ctx.has_flag("starter_chosen"):
        return
    starters: list[tuple[str, int]] = [("Turtwig", 387), ("Chimchar", 390), ("Piplup", 393)]
    injected = action.get("choice")
    if injected is not None:
        if isinstance(injected, int):
            injected_idx = max(1, min(len(starters), injected))
            species_id = starters[injected_idx-1][1]
        else:
            name_l = str(injected).lower()
            species_id = next((sid for label, sid in starters if label.lower().startswith(name_l)), starters[0][1])
    else:
        # Fallback: if stdin not interactive (e.g., during automated tests), auto-pick first starter
        try:
            import sys
            if not sys.stdin.isatty():
                species_id = starters[0][1]
            else:
                options = [(label, str(sid)) for label, sid in starters]
                sel = select_menu("Choose your starter", options, footer="↑/↓ or W/S to move • Enter to select")
                if sel is None:
                    print("Starter selection cancelled.")
                    return
                species_id = int(sel)
        except Exception:
            species_id = starters[0][1]
    species_name = _STARTERS[species_id]
    from platinum.battle.experience import clamp_level as _cl
    ctx.state.party.append(PartyMember(species=species_name, level=_cl(5), hp=22, max_hp=22))
    print(f"Added {species_name.capitalize()} (#{species_id}) to your party!")
    rival_id = _RIVAL_COUNTER[species_id]
    rival_name = _STARTERS[rival_id]
    ctx.set_flag(f"rival_starter_{rival_name}")
    print("Starter selected. Proceeding...")

COMMANDS = {
    "SHOW_TEXT": handle_show_text,
    "SET_FLAG": handle_set_flag,
    "CLEAR_FLAG": handle_clear_flag,
    "START_BATTLE": handle_start_battle,
    "SET_LOCATION": handle_set_location,
    "ADD_PARTY": handle_add_party,
    "CHOOSE_STARTER": handle_choose_starter,
    # WAIT_INPUT: simple pause to pace story progression; skipped in automated test environments
    "WAIT_INPUT": lambda ctx, action: (None if __import__('os').getenv('PYTEST_CURRENT_TEST') else input(action.get('prompt', 'Press Enter to continue...')))
}

def run_action(ctx, action: dict):
    cmd = action.get("command")
    if not isinstance(cmd, str):
        print("[events] Missing command field")
        return
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"[events] Unknown command: {cmd}")
        return
    fn(ctx, action)