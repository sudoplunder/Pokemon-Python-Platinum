from __future__ import annotations
from typing import Any
from platinum.system.save import PartyMember
from platinum.battle.experience import clamp_level
from platinum.battle.experience import required_exp_for_level, growth_rate
from platinum.data.species_lookup import species_id as _species_id, species_name as _species_name
from platinum.data.loader import get_species, possible_evolutions
from platinum.battle.factory import derive_stats
from platinum.ui.menu_nav import select_menu, Menu, MenuItem
from colorama import Fore, Style
from platinum.audio.player import audio
from platinum.ui import typewriter as tw
from pathlib import Path

"""Event script command handlers (with arrow/W/S starter selection)."""

_STARTERS: dict[int, str] = {387: "turtwig", 390: "chimchar", 393: "piplup"}
_RIVAL_COUNTER: dict[int, int] = {387: 390, 390: 393, 393: 387}

def handle_show_text(ctx, action: dict):
    key = action.get("dialogue_key")
    if not key:
        print("[events] SHOW_TEXT missing dialogue_key")
        return
    try:
        ctx.dialogue.show(key)
    except Exception:
        print(f"[Missing dialogue: {key}]")


def handle_set_flag(ctx, action: dict):
    f = action.get("flag")
    if f:
        ctx.set_flag(f)


def handle_clear_flag(ctx, action: dict):
    f = action.get("flag")
    if f:
        ctx.clear_flag(f)


def handle_play_sfx(ctx, action: dict):
    key = action.get("key")
    path = action.get("path")
    blocking = bool(action.get("blocking", True))
    volume = action.get("volume")
    if not path and key:
        try:
            root = Path(__file__).resolve().parents[2]
            path = str(root / "assets" / "audio" / "sfx" / f"{key}.ogg")
        except Exception:
            path = f"assets/audio/sfx/{key}.ogg"
    if not path:
        return
    try:
        if blocking:
            audio.play_sfx_blocking(path, volume=volume)
        else:
            audio.play_sfx(path, volume=volume)
    except Exception:
        pass


def handle_give_item(ctx, action: dict):
    # Supports either value={item, quantity} or explicit fields
    val = action.get("value") or {}
    # Prefer "key" for inventory, fallback to "item", then val fields
    item_key = action.get("key") or val.get("item") or action.get("item")
    # Use "item" for display name, fallback to key
    item_display_name = action.get("item") or item_key
    qty = int(action.get("amount") or val.get("quantity") or 1)
    pocket_name = action.get("pocket", "Items")  # Default pocket name
    
    if not item_key:
        return
    
    try:
        # Add item to inventory
        inv = getattr(ctx.state, 'inventory', None)
        if inv is None:
            inv = {}
            setattr(ctx.state, 'inventory', inv)
        inv[item_key] = inv.get(item_key, 0) + max(1, qty)
        
        # Enhanced item giving experience
        try:
            from platinum.audio.player import audio
            from platinum.ui import typewriter as tw
            from platinum.system.settings import Settings
            from pathlib import Path
            
            # Pause current overworld music
            prev_music_path = None
            try:
                prev_music_path = getattr(audio, "_state").last_path
                audio.stop_music()
            except Exception:
                pass
            
            # Display item received message with sound
            try:
                tw.clear_screen()
            except Exception:
                pass
            
            # Format item name and quantity
            item_display = (item_display_name or item_key).replace('-', ' ').replace('_', ' ').title()
            if qty > 1:
                qty_text = f"{qty}x "
            else:
                qty_text = ""
            
            # Show item received message with timed sound
            received_text = f"You received {qty_text}{item_display}!"
            
            # Play item received sound right as the message appears
            try:
                root = Path(__file__).resolve().parents[2]
                sfx_path = root / "assets" / "audio" / "sfx" / "got_an_item.ogg"
                if sfx_path.exists():
                    # Start sound non-blocking so it plays during message
                    audio.play_sfx(str(sfx_path))
            except Exception:
                pass
            
            try:
                text_speed = Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2
                tw.type_out(received_text, text_speed)
                tw.wait_for_continue()
            except Exception:
                # Fallback to simple print
                print(received_text)
                input("Press Enter to continue...")
                try:
                    tw.clear_screen()
                except Exception:
                    pass
            
            # Resume overworld music
            if prev_music_path:
                try:
                    audio.play_music(prev_music_path, loop=True)
                except Exception:
                    pass
            
            # Show pocket placement message
            if qty > 1:
                item_possessive = "items"
            else:
                item_possessive = "item"
            
            pocket_text = f"Placed the {item_possessive} in the {pocket_name} pocket!"
            try:
                text_speed = Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2
                tw.type_out(pocket_text, text_speed)
                tw.wait_for_continue()
            except Exception:
                # Fallback to simple print
                print(pocket_text)
                input("Press Enter to continue...")
                try:
                    tw.clear_screen()
                except Exception:
                    pass
            
            
        except Exception:
            # Fallback to simple message
            item_display = (item_display_name or item_key).replace('-', ' ').replace('_', ' ').title()
            print(f"You received {qty}x {item_display}!")
            print(f"Placed the items in the {pocket_name} pocket!")
            input("Press Enter to continue...")
            try:
                from platinum.ui import typewriter as tw
                tw.clear_screen()
            except Exception:
                pass
        
    except Exception:
        # Fallback to simple message if enhanced version fails
        print(f"Received {(item_display_name or item_key).replace('-', ' ').title()} x{qty}")


def handle_play_music(ctx, action: dict):
    """Play BGM from assets/audio/bgm with optional snapshot of current track.

    Action fields:
    - key: logical key under assets/audio/bgm (e.g., "rowan_intro")
    - path: explicit path to an audio file; overrides key if provided
    - intro_key: logical key for intro music; if provided with key, plays intro then loops key
    - snapshot: if true, remember current music so later flows can restore it.
                For the Rowan intro flow, we store it under ctx.state._rowan_intro_prev_music.
    - loop: whether to loop the music (default True)
    - volume: optional float volume (0..1)
    """
    key = action.get("key")
    path = action.get("path")
    intro_key = action.get("intro_key")
    loop = bool(action.get("loop", True))
    volume = action.get("volume")
    take_snapshot = bool(action.get("snapshot", False))
    # Best-effort snapshot of current music path before swapping
    if take_snapshot:
        try:
            prev = getattr(audio, "_state").last_path
            if prev:
                setattr(ctx.state, "_rowan_intro_prev_music", prev)
        except Exception:
            pass
            
    # Handle intro/loop sequence
    if intro_key and key:
        try:
            root = Path(__file__).resolve().parents[2]
            intro_path = str(root / "assets" / "audio" / "bgm" / f"{intro_key}.ogg")
            loop_path = str(root / "assets" / "audio" / "bgm" / f"{key}.ogg")
            audio.play_intro_loop_music(intro_path, loop_path)
            if volume is not None:
                audio.set_music_volume(float(volume))
            return
        except Exception:
            pass
    
    # Resolve path for single music file
    if not path and key:
        try:
            root = Path(__file__).resolve().parents[2]
            path = str(root / "assets" / "audio" / "bgm" / f"{key}.ogg")
        except Exception:
            path = f"assets/audio/bgm/{key}.ogg"
    if not path:
        return
    try:
        # Check for custom loop points if looping is enabled
        if loop:
            from platinum.audio.loop_example import load_loop_points
            loop_start, loop_end = load_loop_points(path)
            
            if loop_start is not None or loop_end is not None:
                audio.play_music(path, loop=True, loop_start=loop_start, loop_end=loop_end)
            else:
                audio.play_music(path, loop=loop)
        else:
            audio.play_music(path, loop=loop)
            
        if volume is not None:
            audio.set_music_volume(float(volume))
    except Exception:
        pass


def handle_start_battle(ctx, action: dict):
    """Start a battle with optional interactive UI and trainer/wild post-flow.

    Fields: battle_id, interactive (bool), trainer (bool), trainer_label (str),
            enemy_species (id or name), level (int)
    """
    bid = action.get("battle_id", "unknown")
    interactive = bool(action.get("interactive", False))
    is_trainer = bool(action.get("trainer", False))
    trainer_label = action.get("trainer_label")
    enemy_species = action.get("enemy_species")
    enemy_level = int(action.get("level", 5))

    # Snapshot current music path to resume after battle
    try:
        prev_music = getattr(audio, "_state").last_path
    except Exception:
        prev_music = None
    is_rival_battle = is_trainer and ((trainer_label or '').lower().startswith('rival') or 'rival' in bid)

    if interactive:
        try:
            if bid:
                print(str(bid))
        except Exception:
            pass
        from platinum.battle.factory import battler_from_species
        from platinum.data.species_lookup import species_id
        from platinum.ui.battle import run_battle_ui
        from platinum.battle.session import Party, BattleSession
        from platinum.battle.experience import exp_gain, apply_experience

        # Build player's battlers from saved party (preserving HP/Status/PP)
        player_battlers: list[Any] = []
        for pm in ctx.state.party:
            try:
                sid = species_id(pm.species) if isinstance(pm.species, str) else int(pm.species)
            except Exception:
                continue
            b = battler_from_species(sid, pm.level, nickname=str(pm.species).capitalize())
            try:
                b.current_hp = max(0, min(int(getattr(pm, 'hp', b.stats['hp'])), int(b.stats['hp'])))
            except Exception:
                b.current_hp = b.stats['hp']
            b.status = (pm.status or 'none') if hasattr(pm, 'status') else 'none'
            # Seed moves and PP
            try:
                from platinum.data.moves import get_move as _get_move
                from platinum.battle.core import Move as _BCMove
                pm_moves = list(getattr(pm, 'moves', []) or [])
                pm_pp = dict(getattr(pm, 'move_pp', {}) or {})
                new_moves = []
                for m_internal in pm_moves[:4]:
                    md = _get_move(m_internal)
                    _dr = md.get("drain"); drain_ratio = tuple(_dr) if isinstance(_dr, (list, tuple)) else None
                    _rr = md.get("recoil"); recoil_ratio = tuple(_rr) if isinstance(_rr, (list, tuple)) else None
                    _mh = md.get("multi_hit"); hits = tuple(_mh) if isinstance(_mh, (list, tuple)) else None
                    multi_turn = md.get("multi_turn")
                    if multi_turn is not None and not isinstance(multi_turn, (list, tuple)):
                        multi_turn = None
                    new_moves.append(_BCMove(
                        name=md["display_name"], type=md.get("type") or b.types[0], category=md.get("category") or "status",
                        power=md.get("power") or 0, accuracy=md.get("accuracy"), priority=md.get("priority", 0),
                        crit_rate_stage=md.get("crit_rate_stage", 0), hits=hits, drain_ratio=drain_ratio, recoil_ratio=recoil_ratio,
                        flinch_chance=md.get("flinch_chance", 0), ailment=md.get("ailment"), ailment_chance=md.get("ailment_chance", 0),
                        stat_changes=[{"stat": sc.get("stat"), "change": sc.get("change"), "chance": sc.get("chance", 0)} for sc in md.get("stat_changes", [])],
                        target=md.get("targets") or "selected-pokemon", flags={"internal": m_internal} | (md.get("flags", {}) or {}),
                        multi_turn=tuple(multi_turn) if multi_turn else None, max_pp=md.get("pp", 0) or 0,
                        pp=pm_pp.get(m_internal, md.get("pp", 0) or 0),
                    ))
                if new_moves:
                    b.moves = new_moves
            except Exception:
                pass
            player_battlers.append(b)

        # Obedience badge count hint
        badge_count = len(getattr(ctx.state, 'badges', []))
        for b in player_battlers:
            setattr(b, 'badge_count', badge_count)

        # Enemy battlers (Rival special-case -> type-advantage starter; else from config or single)
        enemy_battlers: list[Any] = []
        enemy_sid: int | None = None
    # Prefer config-driven party; rival starter is selected via requires_flag in config
        # Try to load battle config by id
        cfg = None
        try:
            import json
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            cfg_dir = root / "assets" / "battle_configs"
            # brute-force scan; small count
            for fp in cfg_dir.rglob("*.json"):
                try:
                    raw = json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if str(raw.get("id")) == str(bid):
                    cfg = raw
                    break
        except Exception:
            cfg = None
        if not enemy_battlers and cfg and isinstance(cfg.get("party"), list):
            try:
                from platinum.data.loader import get_species as _get_species
            except Exception:
                _get_species = None
            for slot in cfg["party"]:
                # Optional gating via requires_flag on each party slot
                req = slot.get("requires_flag")
                if req and not getattr(ctx, 'has_flag', lambda f: False)(req):
                    continue
                try:
                    sp = slot.get("species")
                    lvl = int(slot.get("level", enemy_level))
                    sid = species_id(sp) if isinstance(sp, str) else int(sp)
                    # Capture first enemy's species ID for EXP calculation
                    if enemy_sid is None:
                        enemy_sid = sid
                except Exception:
                    continue
                try:
                    e_name = _get_species(sid)["name"].capitalize() if _get_species else str(sp).capitalize()
                except Exception:
                    e_name = str(sp).capitalize()
                enemy_battlers.append(battler_from_species(sid, lvl, nickname=e_name))
            # Fallback trainer label
            if is_trainer and not trainer_label:
                lab = cfg.get("trainer")
                if isinstance(lab, str) and lab:
                    trainer_label = lab.title() if lab.lower() != "rival" else (f"Rival ({getattr(ctx.state,'rival_name','Barry')})")
            try:
                print(f"[DEBUG] Loaded battle config for {bid}: {len(enemy_battlers)} enemy(s)")
            except Exception:
                pass
        if not enemy_battlers and enemy_species is not None:
            try:
                enemy_sid = species_id(enemy_species) if isinstance(enemy_species, str) else int(enemy_species)
            except Exception:
                enemy_sid = None
            if enemy_sid is not None:
                try:
                    from platinum.data.loader import get_species as _get_species
                    e_name = _get_species(enemy_sid)["name"].capitalize()
                except Exception:
                    e_name = str(enemy_species).capitalize()
                enemy_battlers.append(battler_from_species(enemy_sid, enemy_level, nickname=e_name))
        if not enemy_battlers:
            # Ultimate fallback: demo battle service
            try:
                print(f"[DEBUG] No enemy configured for {bid}; using demo service")
            except Exception:
                pass
            res = ctx.battle_service.start(bid)
            if getattr(ctx.settings.data, 'debug', False):
                print(f"[battle] Result: {res['outcome']}")
            if res['outcome'] == 'PLAYER_WIN':
                ctx.set_flag(f"battle_{bid}_won")
            else:
                ctx.set_flag(f"battle_{bid}_lost")
            return

        session = BattleSession(Party(player_battlers), Party(enemy_battlers), is_wild=not is_trainer)
        if getattr(ctx.settings.data, 'debug', False):
            print(f"[battle] (interactive) {bid}")

        if is_trainer and not trainer_label:
            rival_name = getattr(ctx.state, 'rival_name', None)
            if is_rival_battle:
                trainer_label = f"Rival ({rival_name})" if rival_name else "Rival"

        try:
            # Debug banner for rival battle start
            if bid == "rival_battle_1":
                try:
                    flags_sorted = sorted(list(getattr(ctx, 'flags', set())))
                except Exception:
                    flags_sorted = []
                print(f"[DEBUG] Starting rival battle 1. Trainer label: {trainer_label}. Flags: {flags_sorted}")
            outcome = run_battle_ui(session, is_trainer=is_trainer, trainer_label=trainer_label)
        except TypeError:
            outcome = run_battle_ui(session, is_trainer=is_trainer)

        # Record flags
        if outcome == 'PLAYER_WIN':
            ctx.set_flag(f"battle_{bid}_won")
        elif outcome == 'PLAYER_LOSS':
            ctx.set_flag(f"battle_{bid}_lost")
        elif outcome == 'ESCAPE':
            ctx.set_flag(f"battle_{bid}_escape")

        # On win: post-battle EXP and flows
        if outcome == 'PLAYER_WIN' and enemy_sid is not None:
            # Clear HUD
            try:
                tw.clear_screen()
            except Exception:
                pass
            # Wild victory jingle first
            if not is_trainer:
                try:
                    audio.stop_music()
                except Exception:
                    pass
                try:
                    audio.play_sfx_blocking("assets/audio/sfx/victory_wild_battle.ogg", volume=1.0)
                except Exception:
                    pass
            # Participants
            try:
                part_indices = set(getattr(session, 'player_participants', {session.player.active_index}))
            except Exception:
                part_indices = {session.player.active_index}
            participants = max(1, len(part_indices))

            def _sid_for(val):
                from platinum.data.species_lookup import species_id as _sid_loc
                try:
                    return _sid_loc(val) if isinstance(val, str) else int(val)
                except Exception:
                    return None

            def _animate_xp(member, gained_exp: int):
                try:
                    sid_local = _sid_for(member.species)
                except Exception:
                    sid_local = None
                rate_name = growth_rate(sid_local) if sid_local is not None else 'Medium Fast'
                start_exp = getattr(member, 'exp', 0)
                start_level = member.level
                target_exp = start_exp + max(0, int(gained_exp))
                cur_exp = start_exp
                cur_level = start_level
                import time
                while cur_exp < target_exp and cur_level < 100:
                    cur_req = required_exp_for_level(cur_level, rate=rate_name)
                    next_req = required_exp_for_level(cur_level + 1, rate=rate_name) if cur_level < 100 else cur_req + 1
                    step_to = min(target_exp, next_req)
                    steps = max(1, (step_to - cur_exp) // 8)
                    cur_exp = min(step_to, cur_exp + steps)
                    print(f"{member.species.capitalize()} gaining EXP... {cur_exp - start_exp}/{gained_exp}")
                    try:
                        time.sleep(0.02)
                    except Exception:
                        pass
                    if cur_exp >= next_req and cur_level < 100:
                        cur_level += 1
                        print(f"{member.species.capitalize()} leveled up to Lv{cur_level}!")
                        try:
                            time.sleep(0.05)
                        except Exception:
                            pass
                before_level = member.level
                before_moves = list(getattr(member, 'moves', []) or [])
                before_sid = _sid_for(member.species)
                try:
                    base_stats = get_species(before_sid)["base_stats"]
                    stats_before = derive_stats(base_stats, before_level)
                except Exception:
                    stats_before = {k: getattr(member, k, 0) for k in ("hp","attack","defense","sp_atk","sp_def","speed")}
                res_local = apply_experience(member, gained_exp, species_id=before_sid)
                after_level = member.level
                try:
                    base_stats = get_species(before_sid)["base_stats"]
                    stats_after = derive_stats(base_stats, after_level)
                except Exception:
                    stats_after = stats_before
                if after_level > before_level:
                    try:
                        tw.clear_screen()
                    except Exception:
                        pass
                    print(f"{member.species.capitalize()} grew to level {after_level}!")
                    def _line(label: str, delta: int):
                        return f"{label} +{delta}" if delta > 0 else f"{label}"
                    print(_line("HP", stats_after.get("hp",0) - stats_before.get("hp",0)))
                    print(_line("Attack", stats_after.get("attack",0) - stats_before.get("attack",0)))
                    print(_line("Defense", stats_after.get("defense",0) - stats_before.get("defense",0)))
                    print(_line("Sp. Atk", stats_after.get("sp_atk",0) - stats_before.get("sp_atk",0)))
                    print(_line("Sp. Def", stats_after.get("sp_def",0) - stats_before.get("sp_def",0)))
                    print(_line("Speed", stats_after.get("speed",0) - stats_before.get("speed",0)))
                    learned_moves = list(res_local.get('learned') or [])
                    if learned_moves:
                        moves_now = list(before_moves)
                        for nm in learned_moves:
                            if nm in moves_now:
                                continue
                            if len(moves_now) < 4:
                                print(f"{member.species.capitalize()} wants to learn {nm.replace('-', ' ').title()}.")
                                choice = Menu("Learn this move?", [MenuItem("Learn","yes"), MenuItem("Give up","no")], allow_escape=True).run()
                                if choice == "yes":
                                    moves_now.append(nm)
                            else:
                                print(f"{member.species.capitalize()} wants to learn {nm.replace('-', ' ').title()}.")
                                items = [MenuItem(mv.replace('-', ' ').title(), value=mv) for mv in moves_now] + [MenuItem("Give up learning", value="__giveup__")]
                                sel = Menu("Replace which move?", items, allow_escape=True).run()
                                if sel and sel != "__giveup__":
                                    try:
                                        i = moves_now.index(sel)
                                        moves_now[i] = nm
                                    except Exception:
                                        pass
                        member.moves = moves_now[:4]
                    try:
                        possible = possible_evolutions(int(before_sid), level=member.level) if before_sid is not None else []
                    except Exception:
                        possible = []
                    if possible:
                        evo_id = possible[0]
                        print(f"Huh? {member.species.capitalize()} is evolving!")
                        evo_choice = Menu("Evolve now?", [MenuItem("Let it evolve","yes"), MenuItem("Stop evolution (B)","no")], allow_escape=True).run()
                        if evo_choice == "yes":
                            new_name = _species_name(evo_id).capitalize()
                            old_max = getattr(member, 'max_hp', 0)
                            try:
                                new_stats = derive_stats(get_species(evo_id)["base_stats"], member.level)
                            except Exception:
                                new_stats = None
                            member.species = new_name.lower()
                            if new_stats:
                                new_max = int(new_stats.get("hp", old_max or 0))
                                delta = max(0, new_max - int(old_max or 0))
                                member.max_hp = new_max
                                member.hp = min(member.max_hp, int(getattr(member, 'hp', 0)) + delta)

            # Snapshot state before applying to others (debug)
            before_levels = [pm.level for pm in ctx.state.party]
            before_exps = [getattr(pm, 'exp', 0) for pm in ctx.state.party]

            gains: list[int] = []
            for idx, pm in enumerate(ctx.state.party):
                is_part = idx in part_indices
                g = exp_gain(enemy_sid, enemy_level, your_level=pm.level, participants=participants, is_trainer=is_trainer, is_participant=is_part)
                gains.append(g)

            active_idx = session.player.active_index
            if 0 <= active_idx < len(ctx.state.party):
                try:
                    _animate_xp(ctx.state.party[active_idx], gains[active_idx])
                except Exception:
                    try:
                        pm = ctx.state.party[active_idx]
                        sid0 = _sid_for(pm.species)
                        apply_experience(pm, gains[active_idx], species_id=sid0)
                    except Exception:
                        pass
            for idx, pm in enumerate(ctx.state.party):
                if idx == active_idx:
                    continue
                pm_sid = _sid_for(pm.species)
                g = gains[idx]
                try:
                    print(f"{pm.species.capitalize()} gained {g} EXP!")
                    # Removed manual prompt for smoother flow
                except Exception:
                    pass
                res2 = apply_experience(pm, g, species_id=pm_sid)
                if getattr(ctx.settings.data, 'debug', False):
                    msg = f"{pm.species.capitalize()} gained {g} EXP!"
                    if res2['leveled']:
                        msg += f" Grew to Lv{pm.level}!"
                        if res2.get('learned'):
                            learned_str = ", ".join(m.title() for m in res2['learned'])
                            msg += f" Learned {learned_str}!"
                    print(msg)

            # Trainer or wild specific wrap-up
            if is_trainer:
                try:
                    audio.stop_music()
                except Exception:
                    pass
                try:
                    audio.play_sfx_blocking("assets/audio/sfx/victory_trainer_battle.ogg", volume=1.0)
                except Exception:
                    pass
                who = trainer_label or "Trainer"
                print(f"You defeated {who}!")
                try:
                    input("Press Enter to continue...")
                except Exception:
                    pass
                try:
                    tw.clear_screen()
                except Exception:
                    pass
                if (trainer_label or '').lower().startswith('rival'):
                    print("\"W-what just happened. I lost?\"")
                else:
                    print("I- I can’t believe it…")
                try:
                    input("Press Enter to continue...")
                except Exception:
                    pass
                try:
                    tw.clear_screen()
                except Exception:
                    pass
                payout = 1000 if (trainer_label or '').lower().startswith('rival') else 300
                try:
                    ctx.add_money(payout)
                except Exception:
                    ctx.state.money = getattr(ctx.state, 'money', 0) + payout
                print(f"You got {payout:,} for winning!")
                try:
                    input("Press Enter to continue...")
                except Exception:
                    pass
                try:
                    tw.clear_screen()
                except Exception:
                    pass
                try:
                    for member in ctx.state.party:
                        before_sid = _sid_for(member.species)
                        if before_sid is None:
                            continue
                        possible = possible_evolutions(int(before_sid), level=member.level) or []
                        if not possible:
                            continue
                        evo_id = possible[0]
                        print(f"Huh? {member.species.capitalize()} is evolving!")
                        evo_choice = Menu("Evolve now?", [MenuItem("Let it evolve","yes"), MenuItem("Stop evolution (B)","no")], allow_escape=True).run()
                        if evo_choice == "yes":
                            new_name = _species_name(evo_id).capitalize()
                            try:
                                audio.play_sfx_blocking("assets/audio/sfx/evolved.ogg", volume=1.0)
                            except Exception:
                                pass
                            old_max = getattr(member, 'max_hp', 0)
                            try:
                                new_stats = derive_stats(get_species(evo_id)["base_stats"], member.level)
                            except Exception:
                                new_stats = None
                            member.species = new_name.lower()
                            if new_stats:
                                new_max = int(new_stats.get("hp", old_max or 0))
                                delta = max(0, new_max - int(old_max or 0))
                                member.max_hp = new_max
                                member.hp = min(member.max_hp, int(getattr(member, 'hp', 0)) + delta)
                except Exception:
                    pass
                if prev_music:
                    try:
                        audio.play_music(prev_music, loop=True)
                    except Exception:
                        pass
            else:
                # Captured-mon handling (party<=5 else PC up to 200)
                try:
                    cap_sid = getattr(session, '_capture_species_id', None)
                    cap_lvl = int(getattr(session, '_capture_level', enemy_level))
                except Exception:
                    cap_sid = None
                    cap_lvl = enemy_level
                if cap_sid:
                    try:
                        new_species_name = _species_name(int(cap_sid)).lower()
                    except Exception:
                        new_species_name = str(enemy_species).lower() if enemy_species else "unknown"
                    try:
                        pm = PartyMember(species=new_species_name, level=cap_lvl)
                        try:
                            pm.exp = required_exp_for_level(cap_lvl)
                        except Exception:
                            pm.exp = 0
                        try:
                            spec_data = get_species(int(cap_sid))
                            base = spec_data.get("base_stats") or {}
                            stats = derive_stats(base, cap_lvl)
                            pm.max_hp = int(stats.get("hp", pm.max_hp))
                            pm.hp = pm.max_hp
                        except Exception:
                            pass
                        try:
                            from platinum.battle.experience import learn_new_moves
                            from platinum.data.moves import get_move as _get_move
                            learn_new_moves(pm, int(cap_sid))
                            pp_map = {}
                            for mv in pm.moves[:4]:
                                try:
                                    pp_map[mv] = int(_get_move(mv).get("pp", 0) or 0)
                                except Exception:
                                    pp_map[mv] = 0
                            pm.move_pp = pp_map
                        except Exception:
                            pass
                        if len(ctx.state.party) < 6:
                            ctx.state.party.append(pm)
                        else:
                            if len(ctx.state.pc_box) < 200:
                                ctx.state.pc_box.append(pm)
                            else:
                                print("Your PC is full. The Pokémon fled.")
                    except Exception:
                        pass
                if prev_music:
                    try:
                        audio.play_music(prev_music, loop=True)
                    except Exception:
                        pass

            if bid == "rival_battle_1":
                try:
                    print("\n[DEBUG] Barry fight EXP summary:")
                    for i, pm in enumerate(ctx.state.party):
                        gained = gains[i] if i < len(gains) else 0
                        before_lv = before_levels[i] if i < len(before_levels) else getattr(pm, 'level', 1)
                        before_xp = before_exps[i] if i < len(before_exps) else getattr(pm, 'exp', 0)
                        after_lv = getattr(pm, 'level', before_lv)
                        after_xp = getattr(pm, 'exp', before_xp)
                        tag = " LEVEL UP!" if after_lv > before_lv else ""
                        print(f"- {pm.species.capitalize()}: +{gained} XP | Lv {before_lv} ({before_xp}) -> Lv {after_lv} ({after_xp}){tag}")
                    try:
                        input("Press Enter to continue...")
                    except Exception:
                        pass
                except Exception:
                    pass

        # Sync back party HP/Status/PP
        try:
            for idx, b in enumerate(getattr(session.player, 'members', []) or []):
                if idx >= len(ctx.state.party):
                    break
                pm = ctx.state.party[idx]
                try:
                    pm.max_hp = int(b.stats.get('hp', getattr(pm, 'max_hp', 0)))
                except Exception:
                    pass
                try:
                    pm.hp = max(0, int(getattr(b, 'current_hp', getattr(pm, 'hp', 0)) or 0))
                except Exception:
                    pass
                try:
                    pm.status = getattr(b, 'status', getattr(pm, 'status', 'none'))
                except Exception:
                    pass
                try:
                    move_pp = {}
                    for mv in getattr(b, 'moves', []) or []:
                        key = None
                        try:
                            key = mv.flags.get('internal') if hasattr(mv, 'flags') else None
                        except Exception:
                            key = None
                        if not key:
                            continue
                        move_pp[str(key)] = int(getattr(mv, 'pp', 0) or 0)
                    if move_pp:
                        pm.move_pp = move_pp
                except Exception:
                    pass
        except Exception:
            pass
        return

    # Non-interactive path (legacy service)
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
        pm = PartyMember(species=species, level=level, hp=20, max_hp=20)
        # Seed total EXP to the required amount for current level so future gains level correctly
        try:
            pm.exp = required_exp_for_level(level)
        except Exception:
            pm.exp = 0
        # Initialize moves and PP based on learnset
        try:
            from platinum.data.species_lookup import species_id as _sid
            from platinum.battle.experience import learn_new_moves
            from platinum.data.moves import get_move as _get_move
            sid = _sid(species) if isinstance(species, str) else int(species)
            # Fill moves list up to current level (max 4)
            learn_new_moves(pm, sid)
            # Seed PP for each learned move
            pp_map = {}
            for mv in pm.moves[:4]:
                try:
                    pp_map[mv] = int(_get_move(mv).get("pp", 0) or 0)
                except Exception:
                    pp_map[mv] = 0
            pm.move_pp = pp_map
        except Exception:
            pass
        ctx.state.party.append(pm)
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
        # Build colored menu like locations, with white arrow and colored labels
        items: list[MenuItem] = [
            MenuItem(label="Now choose! Which Pokémon will it be?", value="_hdr", disabled=True),
            MenuItem(label="Tiny Leaf Pokémon TURTWIG!", value=str(387), label_color="[green]"),
            MenuItem(label="Chimp Pokémon CHIMCHAR!", value=str(390), label_color="[red]"),
            MenuItem(label="Penguin Pokémon PIPLUP!", value=str(393), label_color="[blue]"),
        ]
        menu = Menu("Choose your starter", items, allow_escape=True, footer="↑/↓ or W/S to move • Enter to select • Esc to cancel")
        while True:
            sel_val = menu.run()
            if sel_val is None:
                print("Starter selection cancelled.")
                return
            if sel_val == "_hdr":
                # If header is focused somehow, advance selection down
                menu._advance(1)
                continue
            chosen_sid = int(sel_val)
            # Confirmation dialog
            confirm_items = [
                MenuItem(label="Are you sure?", value="_hdr", disabled=True),
                MenuItem(label="YES", value="yes"),
                MenuItem(label="NO", value="no"),
            ]
            confirm = Menu("Confirm selection", confirm_items, allow_escape=True, footer="Enter to choose • Esc to cancel").run()
            if confirm is None or confirm == "no":
                # Return to starter list
                menu.index = 1  # default to first starter option
                continue
            if confirm == "yes":
                species_id = chosen_sid
                # Show received message, play evolved sfx over current music, then restore route BGM
                # Show "<PLAYER> received <Starter>!" with fast typewriter
                try:
                    player = getattr(ctx.state, 'player_name', 'PLAYER')
                    from platinum.data.species_lookup import species_name
                    name = species_name(chosen_sid).capitalize() if callable(species_name) else "Starter"
                except Exception:
                    player, name = getattr(ctx.state, 'player_name', 'PLAYER'), "Starter"
                try:
                    tw.clear_screen()
                    tw.type_out(f"{player} received {name}!", 1)
                except Exception:
                    print(f"{player} received {name}!")
                # Ensure Rowan intro ends before SFX; then play SFX; then restore route music
                try:
                    audio.stop_music()
                except Exception:
                    pass
                try:
                    audio.play_sfx_blocking("assets/audio/sfx/evolved.ogg", volume=1.0)
                except Exception:
                    pass
                # If we started Rowan intro earlier, restore previous (route) music now
                restored = False
                try:
                    prev = getattr(ctx.state, "_rowan_intro_prev_music", None)
                except Exception:
                    prev = None
                if prev:
                    try:
                        audio.play_music(prev, loop=True)
                        restored = True
                    except Exception:
                        pass
                    try:
                        delattr(ctx.state, "_rowan_intro_prev_music")
                    except Exception:
                        setattr(ctx.state, "_rowan_intro_prev_music", None)
                if not restored:
                    try:
                        audio.resume_music()
                    except Exception:
                        pass
                break
    species_name = _STARTERS[species_id]
    from platinum.battle.experience import clamp_level as _cl
    pm = PartyMember(species=species_name, level=_cl(5), hp=22, max_hp=22)
    # Seed EXP baseline to the total required for current level
    try:
        pm.exp = required_exp_for_level(pm.level)
    except Exception:
        pm.exp = 0
    # Initialize starter moves and PP immediately so saves contain them
    try:
        from platinum.data.species_lookup import species_id as _sid
        from platinum.battle.experience import learn_new_moves
        from platinum.data.moves import get_move as _get_move
        sid = _sid(species_id)
        learn_new_moves(pm, sid)
        pp_map = {}
        for mv in pm.moves[:4]:
            try:
                pp_map[mv] = int(_get_move(mv).get("pp", 0) or 0)
            except Exception:
                pp_map[mv] = 0
        pm.move_pp = pp_map
    except Exception:
        pass
    ctx.state.party.append(pm)
    print(f"Added {species_name.capitalize()} (#{species_id}) to your party!")
    rival_id = _RIVAL_COUNTER[species_id]
    rival_name = _STARTERS[rival_id]
    # Persist rival pick in flags for events and on state for convenience
    ctx.set_flag(f"rival_starter_{rival_name}")
    setattr(ctx.state, 'rival_starter', rival_name)
    ctx.set_flag('starter_chosen')
    print("Starter selected. Proceeding...")
    # Non-interactive or injected choice path: ensure Rowan intro music (if active) is restored to route BGM
    try:
        prev = getattr(ctx.state, "_rowan_intro_prev_music", None)
    except Exception:
        prev = None
    if prev:
        try:
            audio.play_music(prev, loop=True)
        except Exception:
            pass
        try:
            delattr(ctx.state, "_rowan_intro_prev_music")
        except Exception:
            setattr(ctx.state, "_rowan_intro_prev_music", None)
    try:
        flags_sorted = sorted(list(getattr(ctx, 'flags', set())))
    except Exception:
        flags_sorted = []
    print(f"[DEBUG] Starter chosen: {species_name}; Rival: {rival_name}; Flags: {flags_sorted}")

def handle_trainer_battle(ctx, action: dict):
    """Handle battle using trainer JSON data."""
    trainer_id = action.get("trainer_id")
    if not trainer_id:
        print("[events] TRAINER_BATTLE missing trainer_id")
        return
    
    from platinum.ui.battle import run_trainer_battle
    
    outcome = run_trainer_battle(trainer_id, ctx)
    
    # Set appropriate flags
    if outcome == 'PLAYER_WIN':
        ctx.set_flag(f"trainer_{trainer_id}_defeated")
        ctx.set_flag(f"battle_{trainer_id}_won")
    elif outcome == 'PLAYER_LOSS':
        ctx.set_flag(f"battle_{trainer_id}_lost")

COMMANDS = {
    "SHOW_TEXT": handle_show_text,
    "SET_FLAG": handle_set_flag,
    "CLEAR_FLAG": handle_clear_flag,
    # "START_BATTLE": handle_start_battle,  # DEPRECATED: Use TRAINER_BATTLE instead
    "SET_LOCATION": handle_set_location,
    "ADD_PARTY": handle_add_party,
    "CHOOSE_STARTER": handle_choose_starter,
    "PLAY_MUSIC": handle_play_music,
    "PLAY_SFX": handle_play_sfx,
    "GIVE_ITEM": handle_give_item,
    "TRAINER_BATTLE": handle_trainer_battle,
    # DEBUG_PRINT: log a message and optionally current flags for troubleshooting
    "DEBUG_PRINT": lambda ctx, action: (print(action.get("message", "[DEBUG]")) or (print(f"[DEBUG] Flags: {sorted(list(getattr(ctx, 'flags', set()))) }") if action.get("dump_flags") else None)),
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