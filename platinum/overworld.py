from __future__ import annotations
"""Data-driven overworld navigation using nested location JSON.

Location JSON structure (example at assets/locations/overworld.json):
{
  "id": "twinleaf_town_bedroom",
  "name": "Bedroom",
  "actions": [ { ... } ],
  "children": [ { nested locations } ]
}

Action types:
- move: change location to target id
- inspect: print text; optional set_flag
- dialogue: show dialogue_key if available else fallback_text; optional set_flag
- exit: return to main menu (ends overworld loop)

Flags: actions may specify set_flag to raise event flags.
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from platinum.ui.menu_nav import select_menu, Menu, MenuItem
from platinum.ui.keys import Key, read_key
from platinum.ui.menu import options_submenu
from platinum.ui import typewriter as tw
from platinum.system.settings import Settings
from platinum.audio.player import audio
from platinum.system.save import save_game, delete_temp

# Rich imports for structured bag display
from rich.console import Console
from rich.table import Table
from rich.align import Align
from rich.panel import Panel
from rich import box
from rich.box import ROUNDED

# Rich imports for beautiful overworld UI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.box import ROUNDED, DOUBLE
from rich import print as rprint

# Global Rich console
overworld_console = Console()

LOCATIONS_DIR = Path("assets/locations")
INDEX_FILE = LOCATIONS_DIR / "overworld.json"  # legacy single-file or index (contains root_id)

@dataclass
@dataclass
class Action:
    label: str
    type: str
    target: Optional[str] = None
    text: Optional[str] = None
    night_text: Optional[str] = None
    dialogue_key: Optional[str] = None
    fallback_text: Optional[str] = None
    set_flag: Optional[str] = None
    zone: Optional[str] = None
    method: Optional[str] = None
    requires_flag: Optional[str] = None
    requires_not_flag: Optional[str] = None
    flag: Optional[str] = None  # For set_flag action type
    species: Optional[str] = None  # For catch_pokemon action type
    level: Optional[int] = None  # For catch_pokemon action type
    message: Optional[str] = None  # For custom messages
    trainer_id: Optional[str] = None  # For trainer_battle action type

@dataclass
class LocationNode:
    id: str
    name: str
    music: Optional[str] = None
    actions: List[Action] = field(default_factory=list)
    children: List['LocationNode'] = field(default_factory=list)

    def collect(self) -> Dict[str,'LocationNode']:
        result: Dict[str, LocationNode] = {self.id: self}
        for child in self.children:
            child_map = child.collect()
            for k, v in child_map.items():
                result[k] = v
        return result

def _load_locations() -> tuple[LocationNode | None, Dict[str, LocationNode]]:
    """Load locations from either:
      1. Multiple *.location.json files (preferred modular approach) OR
      2. Legacy nested overworld.json (acts as index) if modular files absent.

    Returns (root_node, nodes_by_id)
    """
    nodes: Dict[str, LocationNode] = {}
    root_id: Optional[str] = None

    # Modular: each file defines a single location (no deep nesting) with optional children (list of ids)
    if LOCATIONS_DIR.is_dir():
        for f in LOCATIONS_DIR.glob("*.location.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if 'id' not in data:
                continue
            actions = [Action(**a) for a in data.get('actions', [])]
            loc = LocationNode(id=data['id'], name=data.get('name', data['id']), music=data.get('music'), actions=actions, children=[])
            nodes[loc.id] = loc
            if data.get('root') is True:
                root_id = loc.id
        # Link children references
        for f in LOCATIONS_DIR.glob("*.location.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            cid = data.get('id')
            if not cid or cid not in nodes:
                continue
            for child_id in data.get('children', []) or []:
                child = nodes.get(child_id)
                if child and child not in nodes[cid].children:
                    nodes[cid].children.append(child)
        # Fallback root id: first file
        if not root_id and nodes:
            root_id = sorted(nodes.keys())[0]
    # Legacy single nested file path
    if not nodes and INDEX_FILE.is_file():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return (None, {})
        def build(node: dict) -> LocationNode:
            actions = [Action(**a) for a in node.get('actions', [])]
            children = [build(c) for c in node.get('children', [])]
            ln = LocationNode(id=node['id'], name=node.get('name', node['id']), music=node.get('music'), actions=actions, children=children)
            return ln
        root = build(data)
        nodes = root.collect()
        root_id = root.id
        return (root, nodes)

    root = nodes.get(root_id) if root_id else None
    return (root, nodes)


def _apply_wild_experience_immediate(ctx, session, *, enemy_species: int, enemy_level: int):
    """Apply XP immediately when wild Pokemon faints (proper battle sequence)."""
    try:
        from platinum.battle.experience import exp_gain, apply_experience, growth_rate, required_exp_for_level
        from platinum.battle.factory import derive_stats
        from platinum.data.species_lookup import species_id
        from platinum.data.loader import get_species, level_up_learnset
        from platinum.ui.battle import _handle_multiple_level_ups
        
        # Determine participants (active battlers)
        try:
            part_indices = set(getattr(session, 'player_participants', {session.player.active_index}))
        except Exception:
            part_indices = {session.player.active_index}
        participants = max(1, len(part_indices))
        
        def _sid_for(val):
            try:
                return species_id(val) if isinstance(val, str) else int(val)
            except Exception:
                return None
        
        # Calculate XP gains for all party members
        for idx, pm in enumerate(ctx.state.party):
            is_part = idx in part_indices
            gained_xp = exp_gain(enemy_species, enemy_level, your_level=pm.level, participants=participants, is_trainer=False, is_participant=is_part)
            
            # Store pre-level data for stat comparison
            pre_level = pm.level
            pre_exp = getattr(pm, 'exp', 0)
            pm_sid = _sid_for(pm.species)
            
            # Calculate pre-level stats
            try:
                base_stats = get_species(pm_sid)["base_stats"] if pm_sid else {}
                pre_stats = derive_stats(base_stats, pre_level) if base_stats else {}
            except Exception:
                pre_stats = {}
            
            # Apply XP and process any level-ups
            res = apply_experience(pm, gained_xp, species_id=pm_sid)
            
            # Display XP gain
            print(f"{pm.species.capitalize()} gained {gained_xp} EXP!")
            
            # Handle level-ups with proper Pokemon sequence
            if res['leveled']:
                levels_gained = pm.level - pre_level
                _handle_multiple_level_ups(ctx, pm, pm_sid, pre_level, pre_stats, levels_gained, battle_session=session)
                    
    except Exception as e:
        print(f"[XP] Error applying immediate wild experience: {e}")


def _apply_wild_experience(ctx, session, *, enemy_species: int, enemy_level: int):
    """Apply BDSP-style shared XP to all party members after wild battle victory."""
    try:
        from platinum.battle.experience import exp_gain, apply_experience
        from platinum.data.species_lookup import species_id
        
        # Determine participants (active battlers)
        try:
            part_indices = set(getattr(session, 'player_participants', {session.player.active_index}))
        except Exception:
            part_indices = {session.player.active_index}
        participants = max(1, len(part_indices))
        
        def _sid_for(val):
            try:
                return species_id(val) if isinstance(val, str) else int(val)
            except Exception:
                return None
        
        # Calculate XP gains for all party members
        for idx, pm in enumerate(ctx.state.party):
            is_part = idx in part_indices
            gained_xp = exp_gain(enemy_species, enemy_level, your_level=pm.level, participants=participants, is_trainer=False, is_participant=is_part)
            
            # Apply XP
            pm_sid = _sid_for(pm.species)
            res = apply_experience(pm, gained_xp, species_id=pm_sid)
            
            # Simple XP notification
            print(f"{pm.species.capitalize()} gained {gained_xp} EXP!")
            if res['leveled']:
                print(f"{pm.species.capitalize()} grew to level {pm.level}!")
                if res.get('learned'):
                    learned_str = ", ".join(m.title().replace('-', ' ') for m in res['learned'])
                    print(f"Learned {learned_str}!")
                    
    except Exception as e:
        print(f"[XP] Error applying wild experience: {e}")


def run_overworld(ctx):
    root, all_nodes = _load_locations()
    if not root or not all_nodes:
        print("[overworld] Missing locations file.")
        return
    # Ensure current location is valid; else snap to root
    if ctx.state.location not in all_nodes:
        ctx.set_location(root.id)
    
    # Track last displayed location for announcements
    last_announced_location = None
    last_music_key: Optional[str] = None
    
    while True:
        # Helper to render a standalone text block like dialogue: clear -> type -> wait
        def _show_text_block(text: str):
            try:
                speed = Settings.load().data.text_speed
            except Exception:
                speed = 2
            try:
                tw.clear_screen()
            except Exception:
                pass
            # Multi-line semantics: pause and clear between each line
            lines = str(text).split('\n')
            if not lines:
                lines = [str(text)]
            for i, ln in enumerate(lines):
                tw.type_out(ln, speed)
                tw.wait_for_continue()
                if i < len(lines) - 1:
                    try:
                        tw.clear_screen()
                    except Exception:
                        pass
        # Auto-refresh real time -> system_time & time_of_day every tick
        try:
            from datetime import datetime
            now = datetime.now()
            ctx.state.system_time = now.strftime('%H:%M')
            h = now.hour
            if 5 <= h < 10:
                ctx.state.time_of_day = 'morning'
            elif 10 <= h < 18:
                ctx.state.time_of_day = 'day'
            elif 18 <= h < 22:
                ctx.state.time_of_day = 'evening'
            else:
                ctx.state.time_of_day = 'night'
        except Exception:
            pass
        node = all_nodes.get(ctx.state.location)
        if not node:
            print("[overworld] Unknown location; exiting.")
            return
            
        # Announce location when first entering or changing locations
        if last_announced_location != ctx.state.location:
            # Centered typewriter banner that auto-dismisses after ~2s
            try:
                import shutil, time, os
                cols = shutil.get_terminal_size((80, 20)).columns
                title = str(node.name).strip()
                tw.clear_screen()
                # Center the location name
                pad = max(0, (cols - len(title)) // 2)
                # Force fastest speed for banner regardless of global setting
                tw.type_out(" " * pad + title, 1)
                if not os.getenv('PYTEST_CURRENT_TEST'):
                    time.sleep(1.5)
                # Clear before showing menu
                tw.clear_screen()
            except Exception:
                pass
            last_announced_location = ctx.state.location
            # Handle location music with night theme support
            key = node.music
            if key:
                # Store original key for comparison
                original_key = key
                
                # Check if this location has night themes and determine which to play
                try:
                    # Get current hour from system_time (stored as "HH:MM" string)
                    current_hour = 12  # Default fallback
                    if hasattr(ctx.state, 'system_time') and ctx.state.system_time:
                        current_hour = int(ctx.state.system_time.split(':')[0])
                except Exception:
                    current_hour = 12
                
                # Night time is from 19:00 (7 PM) to 05:59 (6 AM)
                is_night_time = current_hour >= 19 or current_hour < 6
                
                # Check if night theme exists for this location
                night_key = f"{original_key}_night"
                night_key_alt = original_key.replace("_loop", "_night_loop") if "_loop" in original_key else f"{original_key}_night"
                
                if is_night_time:
                    # Try to use night theme if available (check multiple naming conventions)
                    try:
                        import os
                        night_audio_path = f"assets/audio/bgm/{night_key}.ogg"
                        night_audio_path_alt = f"assets/audio/bgm/{night_key_alt}.ogg"
                        
                        # Check for intro/loop pairs first (preferred for night themes)
                        night_intro_path = f"assets/audio/bgm/{original_key}_night_intro.ogg"
                        night_loop_path = f"assets/audio/bgm/{original_key}_night_loop.ogg"
                        
                        # Check for day/night loop pattern (e.g., pokemon_center_day_loop -> pokemon_center_night_loop)
                        day_night_pattern = original_key.replace("_day", "_night") if "_day" in original_key else None
                        day_night_loop_path = f"assets/audio/bgm/{day_night_pattern}_loop.ogg" if day_night_pattern else None
                        
                        if os.path.exists(night_intro_path) and os.path.exists(night_loop_path):
                            # Use special flag to indicate intro/loop pair
                            key = f"{original_key}_night_intro_loop"
                        elif day_night_loop_path and os.path.exists(day_night_loop_path):
                            # Use day/night loop pattern
                            key = f"{day_night_pattern}_loop"
                        elif os.path.exists(night_audio_path):
                            key = night_key
                        elif os.path.exists(night_audio_path_alt):
                            key = night_key_alt
                    except Exception:
                        pass  # Fall back to regular theme
                else:
                    # During day time, check if we need to use day-specific files or intro/loop pairs
                    try:
                        import os
                        
                        # First check for intro/loop pairs (preferred)
                        intro_path = f"assets/audio/bgm/{original_key}_intro.ogg"
                        loop_path = f"assets/audio/bgm/{original_key}_loop.ogg"
                        
                        # Check if the original key already refers to a loop file
                        original_with_loop = f"assets/audio/bgm/{original_key}_loop.ogg"
                        
                        # Check for day-specific patterns
                        day_pattern = original_key.replace("_night", "_day") if "_night" in original_key else None
                        day_loop_path = f"assets/audio/bgm/{day_pattern}_loop.ogg" if day_pattern else None
                        
                        if os.path.exists(intro_path) and os.path.exists(loop_path):
                            # Use intro/loop pair for daytime
                            key = f"{original_key}_intro_loop"
                        elif os.path.exists(original_with_loop):
                            # Use the _loop version of the original key
                            key = f"{original_key}_loop"
                        elif day_loop_path and os.path.exists(day_loop_path):
                            key = f"{day_pattern}_loop"
                    except Exception:
                        pass
                
                # Always change music when entering a location or when time-based theme changes
                should_change_music = (
                    key != last_music_key or  # Different music key
                    (last_music_key and (original_key in last_music_key or last_music_key in original_key))  # Same location but potential day/night switch
                )
                
                if should_change_music:
                    try:
                        # Check if this is an intro/loop pair
                        if key.endswith("_intro_loop"):
                            # Extract base key and play intro/loop pair
                            base_key = key.replace("_intro_loop", "")
                            intro_path = f"assets/audio/bgm/{base_key}_intro.ogg"
                            loop_path = f"assets/audio/bgm/{base_key}_loop.ogg"
                            audio.play_intro_loop_music(intro_path, loop_path)
                        else:
                            # Regular single file or custom loop points
                            from platinum.audio.loop_example import load_loop_points
                            audio_path = f"assets/audio/bgm/{key}.ogg"
                            loop_start, loop_end = load_loop_points(audio_path)
                            
                            if loop_start is not None or loop_end is not None:
                                audio.play_music(audio_path, loop=True, loop_start=loop_start, loop_end=loop_end)
                            else:
                                audio.play_music(audio_path, loop=True)
                        
                        audio.set_music_volume(0.7)
                        last_music_key = key
                    except Exception:
                        pass
            
        # Build menu (filter by required flags and substitute dynamic labels)
        def _label_with_placeholders(raw: str) -> str:
            lbl = raw
            try:
                player = getattr(ctx.state, 'player_name', '') or 'Player'
                rival = getattr(ctx.state, 'rival_name', '') or 'Rival'
                assistant = getattr(ctx.state, 'assistant', '') or ''
                if not assistant:
                    gender = getattr(ctx.state, 'player_gender', 'male')
                    assistant = 'lucas' if gender == 'female' else 'dawn'
                assistant_disp = str(assistant).title()
                lbl = (lbl.replace('{PLAYER}', player)
                          .replace('{RIVAL}', rival)
                          .replace('{ASSISTANT}', assistant_disp))
            except Exception:
                pass
            return lbl
        visible_actions: list[tuple[str,str]] = []
        for i, a in enumerate(node.actions):
            # Hide legacy Exit items from location menus; use Pause Menu instead
            if a.type == 'exit':
                continue
            if a.requires_flag and not ctx.has_flag(a.requires_flag):
                continue
            if a.requires_not_flag and ctx.has_flag(a.requires_not_flag):
                continue
            visible_actions.append((_label_with_placeholders(a.label), str(i)))
        # Location menus no longer include Save/Exit; B opens pause menu
        menu_items = list(visible_actions)
        title = f"LOCATION: {node.name}"
        choice = select_menu(title, menu_items)
        if choice is None:
            return
        if choice == "__b__":
            # Open pause menu; when it returns, redraw location menu
            _open_pause_menu(ctx)
            continue
        # Handle global non-location actions
        # (no global sentinels in location menu now)
        try:
            idx = int(choice)
        except ValueError:
            # Unknown sentinel, ignore
            continue
        if idx < 0 or idx >= len(node.actions):
            continue
        action = node.actions[idx]
        # Track whether we showed any output requiring a pause before menu redraw
        needs_pause = False
        if action.type == 'move' and action.target:
            if action.target in all_nodes:
                prev = ctx.state.location
                ctx.set_location(action.target)
                if ctx.state.location != prev:
                    # Fire enter_map trigger for event scripts (e.g., lake shore cutscene)
                    try:
                        ctx.events.dispatch_trigger({"type": "enter_map", "value": ctx.state.location})
                    except Exception:
                        pass
            else:
                print("Destination not implemented yet.")
        elif action.type == 'inspect':
            if action.text:
                # Check if it's night time and we have night_text
                txt = action.text
                
                # Handle day-of-week TV show rotation
                if isinstance(txt, dict):
                    from datetime import datetime
                    now = datetime.now()
                    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    current_day = day_names[now.weekday()]
                    txt = txt.get(current_day, txt.get('monday', 'The TV is showing static.'))
                
                try:
                    current_hour = 12  # Default fallback
                    if hasattr(ctx.state, 'system_time') and ctx.state.system_time:
                        current_hour = int(ctx.state.system_time.split(':')[0])
                    
                    # Night time is from 19:00 (7 PM) to 05:59 (6 AM)
                    is_night_time = current_hour >= 19 or current_hour < 6
                    
                    # Use night text if available and it's night time
                    if is_night_time and action.night_text:
                        txt = action.night_text
                except Exception:
                    pass  # Fall back to regular text
                
                if '{SYSTEM_TIME}' in txt:
                    from datetime import datetime
                    now = datetime.now()
                    now_str = now.strftime('%H:%M')
                    ctx.state.system_time = now_str
                    hour = now.hour
                    if 5 <= hour < 10:
                        ctx.state.time_of_day = 'morning'
                    elif 10 <= hour < 18:
                        ctx.state.time_of_day = 'day'
                    elif 18 <= hour < 22:
                        ctx.state.time_of_day = 'evening'
                    else:
                        ctx.state.time_of_day = 'night'
                    txt = txt.replace('{SYSTEM_TIME}', now_str)
                
                # Handle dynamic placeholders for game state
                if '{PARTY_COUNT}' in txt:
                    party_count = len(ctx.state.party) if hasattr(ctx.state, 'party') else 0
                    txt = txt.replace('{PARTY_COUNT}', str(party_count))
                
                if '{FIRST_POKEMON}' in txt:
                    first_pokemon = "your Pokémon"
                    if hasattr(ctx.state, 'party') and ctx.state.party:
                        first_pokemon = getattr(ctx.state.party[0], 'species', 'your Pokémon').capitalize()
                    txt = txt.replace('{FIRST_POKEMON}', first_pokemon)
                
                if '{PARTY_NAMES}' in txt:
                    party_names = "your Pokémon"
                    if hasattr(ctx.state, 'party') and ctx.state.party:
                        names = [getattr(pm, 'species', 'Unknown').capitalize() for pm in ctx.state.party]
                        if len(names) == 1:
                            party_names = names[0]
                        elif len(names) == 2:
                            party_names = f"{names[0]} and {names[1]}"
                        else:
                            party_names = f"{', '.join(names[:-1])}, and {names[-1]}"
                    txt = txt.replace('{PARTY_NAMES}', party_names)
                
                if '{BADGE_COUNT}' in txt:
                    badge_count = 0
                    # Count badge flags (assuming they follow pattern like "badge_1", "badge_2", etc.)
                    for i in range(1, 9):  # Sinnoh has 8 gym badges
                        if ctx.has_flag(f"badge_{i}"):
                            badge_count += 1
                    txt = txt.replace('{BADGE_COUNT}', str(badge_count))
                
                _show_text_block(txt)
                needs_pause = False
            if action.set_flag:
                ctx.set_flag(action.set_flag)
        elif action.type == 'rest':
            # Rest at a bed: show z...z...z and fully heal party statuses + HP
            _show_text_block(action.text or "z... z... z")
            try:
                for pm in ctx.state.party:
                    pm.hp = int(getattr(pm, 'max_hp', getattr(pm, 'hp', 20)) or 20)
                    pm.status = None
                # Small chime? Optional: we keep it silent for tests
            except Exception:
                pass
            needs_pause = False
        elif action.type == 'dialogue':
            # If this dialogue sets a flag and it's already set, treat as repeat -> fallback
            if action.set_flag and ctx.has_flag(action.set_flag):
                if action.fallback_text:
                    _show_text_block(action.fallback_text)
                    needs_pause = False  # handled by _show_text_block
            else:
                if action.dialogue_key:
                    ctx.dialogue.show(action.dialogue_key)
                    needs_pause = False  # dialogue internally prompts once
                elif action.fallback_text:
                    _show_text_block(action.fallback_text)
                    needs_pause = False
                if action.set_flag and not ctx.has_flag(action.set_flag):
                    ctx.set_flag(action.set_flag)
        elif action.type == 'set_flag':
            # Directly set a flag (useful for development/debug commands)
            flag = getattr(action, 'flag', None)
            if flag:
                ctx.set_flag(flag)
                message = getattr(action, 'message', None) or f"Set flag: {flag}"
                _show_text_block(message)
                needs_pause = False
        elif action.type == 'catch_pokemon':
            # Add a Pokemon to the party (development/testing feature)
            species = getattr(action, 'species', None)
            level = getattr(action, 'level', 5)
            set_flag = getattr(action, 'set_flag', None)
            
            if species and len(ctx.state.party) < 6:
                try:
                    from platinum.system.save import PartyMember
                    from platinum.data.species_lookup import species_id
                    
                    # Create the new party member
                    new_pokemon = PartyMember(species=species.lower(), level=int(level))
                    
                    # Add to party
                    ctx.state.party.append(new_pokemon)
                    
                    # Set flag to prevent getting multiple copies
                    if set_flag:
                        ctx.set_flag(set_flag)
                    else:
                        ctx.set_flag(f"{species}_received")
                    
                    _show_text_block(f"A wild {species.capitalize()} joined your party!")
                    needs_pause = False
                    
                except Exception as e:
                    _show_text_block(f"Error adding {species}: {e}")
                    needs_pause = False
            elif len(ctx.state.party) >= 6:
                _show_text_block("Your party is full!")
                needs_pause = False
            else:
                _show_text_block("No species specified.")
                needs_pause = False
        elif action.type == 'pokemon_center':
            # Pokemon Center healing and information
            _show_text_block("Welcome to the Pokémon Center!")
            _show_text_block("We heal your Pokémon to perfect health.")
            
            # Heal all Pokemon in party
            for pm in ctx.state.party:
                try:
                    # Restore HP to max
                    if hasattr(pm, 'max_hp') and hasattr(pm, 'hp'):
                        pm.hp = pm.max_hp
                    elif hasattr(pm, 'level'):
                        # Basic HP calculation if max_hp not set
                        base_hp = 50 + (pm.level * 2)  # Simple formula
                        pm.hp = base_hp
                        pm.max_hp = base_hp
                    
                    # Clear status conditions
                    if hasattr(pm, 'status'):
                        pm.status = 'none'
                    
                    # Restore PP if moves exist
                    if hasattr(pm, 'moves') and hasattr(pm, 'move_pp'):
                        for move in pm.moves:
                            # Restore full PP for each move
                            pm.move_pp[move] = 10  # Default PP
                except Exception:
                    pass
            
            _show_text_block("Your Pokémon have been restored to perfect health!")
            _show_text_block("We hope to see you again!")
            needs_pause = False
        elif action.type == 'poke_mart':
            # Poke Mart shopping
            _show_text_block("Welcome to the Poké Mart!")
            _show_text_block("We have everything a trainer needs.")
            
            # Check gym badges to determine available items
            badges = getattr(ctx.state, 'badges', [])
            badge_count = len(badges)
            
            if badge_count == 0:
                _show_text_block("Standard items available: Poké Ball, Potion, Antidote, Paralyze Heal.")
            elif badge_count >= 1:
                _show_text_block("Expanded stock available! Great Ball, Super Potion, and more items now in stock.")
            
            _show_text_block("Check the right cashier for standard goods.")
            _show_text_block("The left cashier has items unique to this town.")
            needs_pause = False
        elif action.type == 'briefcase':
            # Lake briefcase interaction gating
            if not ctx.has_flag('rival_introduced'):
                _show_text_block("You shouldn't mess with this yet—maybe talk with your friend first.")
                needs_pause = False
            elif ctx.has_flag('starter_chosen'):
                _show_text_block("The briefcase is empty now. Your adventure has begun.")
                needs_pause = False
            elif ctx.has_flag('lake_plan_formed'):
                # Plan already formed; allow retrigger of event chain if starter not chosen
                _show_text_block(action.text or "The briefcase sits here, waiting.")
                ctx.events.dispatch_trigger({"type": "flag_set", "value": "lake_plan_formed"})
                # Mark briefcase inspected for follow-up interaction options
                if action.set_flag and not ctx.has_flag(action.set_flag):
                    ctx.set_flag(action.set_flag)
                needs_pause = False
            else:
                # First time: form plan + trigger
                _show_text_block(action.text or "A professor's briefcase... It looks forgotten.")
                ctx.set_flag('lake_plan_formed')
                # Mark briefcase inspected for follow-up interaction options
                if action.set_flag and not ctx.has_flag(action.set_flag):
                    ctx.set_flag(action.set_flag)
                needs_pause = False
        elif action.type == 'tall_grass_attempt':
            # Attempt to enter grass: if no starter, trigger intercept; else allow future encounter actions
            if ctx.has_flag('starter_chosen'):
                _show_text_block("You step into the tall grass...")
                needs_pause = False
            else:
                ctx.events.dispatch_trigger({"type": "attempt_grass_entry", "value": action.target or action.text or 'route_201'})
        elif action.type == 'surf_attempt':
            # Attempt to surf: check if player has Surf and pokemon that can use it
            fallback_text = action.fallback_text or "The water is deep and blue."
            if ctx.has_flag('surf_unlocked'):
                # Check if player has a pokemon that can use surf
                has_surf_pokemon = False
                surf_pokemon_name = None
                for pm in ctx.state.party:
                    # For now, assume water-type pokemon can use surf
                    # In a more complete implementation, check if pokemon knows Surf move
                    if hasattr(pm, 'species') and pm.species:
                        species_name = pm.species.lower()
                        # Basic water types that can typically learn Surf
                        if any(water_type in species_name for water_type in ['tentacool', 'tentacruel', 'gyarados', 'lapras', 'vaporeon', 'golduck', 'starmie', 'seaking']):
                            has_surf_pokemon = True
                            surf_pokemon_name = pm.species.capitalize()
                            break
                
                if has_surf_pokemon:
                    # Prompt to use surf
                    _show_text_block(f"{fallback_text}")
                    choice = select_menu(
                        f"Would you like to have {surf_pokemon_name} use Surf?",
                        [("Yes", "yes"), ("No", "no")]
                    )
                    if choice == "yes":
                        _show_text_block(f"{surf_pokemon_name} used Surf!")
                        # Allow movement to water areas
                        if action.target and action.target in all_nodes:
                            prev = ctx.state.location
                            ctx.set_location(action.target)
                            if ctx.state.location != prev:
                                try:
                                    ctx.events.dispatch_trigger({"type": "enter_map", "value": ctx.state.location})
                                except Exception:
                                    pass
                        needs_pause = False
                    else:
                        needs_pause = False
                else:
                    _show_text_block(f"{fallback_text} You need a Pokémon that knows Surf!")
                    needs_pause = False
            else:
                _show_text_block(fallback_text)
                needs_pause = False
        elif action.type == 'encounter':
            if not ctx.state.party:
                _show_text_block("You have no Pokémon—Professor Rowan would not approve entering the grass.")
                needs_pause = False
            elif not ctx.has_flag('starter_chosen'):
                _show_text_block("You hesitate—maybe talk to the Professor first.")
                needs_pause = False
            else:
                # Roll a wild encounter from tables and start an interactive battle
                try:
                    from platinum.encounters.loader import roll_encounter, current_time_of_day
                    from platinum.data.species_lookup import species_id
                    from platinum.battle.factory import battler_from_species
                    from platinum.battle.session import Party, BattleSession
                    from platinum.ui.battle import run_battle_ui
                except Exception:
                    _show_text_block("(Encounter data missing.)")
                else:
                    # Simulate searching: 1-5 seconds, one dot per second, then an exclamation
                    try:
                        import random as _rnd, time as _tm, sys as _sys
                        secs = _rnd.randint(1, 5)
                        try:
                            tw.clear_screen()
                        except Exception:
                            pass
                        dots = ""
                        for _ in range(secs):
                            dots += "."
                            print(dots, end="\r", flush=True)
                            _tm.sleep(1)
                        print(dots + "!", flush=True)
                        _tm.sleep(0.4)
                    except Exception:
                        pass
                    zone = action.zone or ctx.state.location
                    m = (action.method or 'grass').lower()
                    method = 'grass'
                    if m in ('grass','cave','water','old_rod'):
                        method = m
                    tod = current_time_of_day(ctx)
                    res = roll_encounter(zone, method, time_of_day=tod)
                    if not res:
                        _show_text_block("(No encounters here.)")
                    else:
                        spc, lvl = res
                        # Build battlers
                        player_battlers = []
                        for pm in ctx.state.party:
                            try:
                                sid = species_id(pm.species) if isinstance(pm.species, str) else int(pm.species)
                            except Exception:
                                continue
                            player_battlers.append(battler_from_species(sid, pm.level, nickname=pm.species.capitalize()))
                        enemy = battler_from_species(int(spc), int(lvl))
                        session = BattleSession(Party(player_battlers), Party([enemy]), is_wild=True)
                        outcome = run_battle_ui(session, is_trainer=False, ctx=ctx)
                        
                        # Wild victory processing is now handled in run_battle_ui
                        # No additional XP or music processing needed here
                needs_pause = False
        elif action.type == 'trainer_battle':
            if action.trainer_id:
                try:
                    from platinum.ui.battle import run_trainer_battle
                    
                    outcome = run_trainer_battle(action.trainer_id, ctx)
                    
                    # Set appropriate flags
                    if outcome == 'PLAYER_WIN':
                        if action.set_flag:
                            ctx.set_flag(action.set_flag)
                        ctx.set_flag(f"trainer_{action.trainer_id}_defeated")
                        ctx.set_flag(f"battle_{action.trainer_id}_won")
                    elif outcome == 'PLAYER_LOSS':
                        ctx.set_flag(f"battle_{action.trainer_id}_lost")
                        
                except Exception as e:
                    _show_text_block(f"Error loading trainer battle: {e}")
            needs_pause = False
        elif action.type == 'trainer_post_battle':
            if action.trainer_id:
                try:
                    # Load trainer data and show post-battle dialogue
                    import json
                    trainer_path = f"assets/trainers/{action.trainer_id}.json"
                    with open(trainer_path, 'r') as f:
                        trainer_data = json.load(f)
                    
                    # Show post-battle dialogue
                    trainer_name = trainer_data.get('name', 'Trainer')
                    post_battle_text = trainer_data.get('post_battle_dialogue', 'Thanks for the battle!')
                    _show_text_block(f"{trainer_name}: {post_battle_text}")
                    
                except Exception as e:
                    _show_text_block(f"Error loading trainer dialogue: {e}")
            needs_pause = False
        elif action.type == 'move_with_trainer_check':
            # Hybrid trainer system: check if all required trainers are defeated
            # For now, implement a simple version - this would need access to all_nodes
            # which is in the main scope. For the moment, let's implement basic logic.
            
            # Check if this is route 202 specifically
            if ctx.state.location == 'route_202':
                undefeated_trainers = []
                if not ctx.has_flag('route_202_youngster_tristan_defeated'):
                    undefeated_trainers.append(('youngster_tristan', 'route_202_youngster_tristan_defeated'))
                if not ctx.has_flag('route_202_youngster_logan_defeated'):
                    undefeated_trainers.append(('youngster_logan', 'route_202_youngster_logan_defeated'))
                if not ctx.has_flag('route_202_lass_beth_defeated'):
                    undefeated_trainers.append(('lass_beth', 'route_202_lass_beth_defeated'))
                
                if undefeated_trainers:
                    # Auto-battle the next undefeated trainer
                    next_trainer_id, next_trainer_flag = undefeated_trainers[0]
                    _show_text_block(f"A trainer blocks your path!")
                    
                    # Execute trainer battle using the proper system
                    try:
                        from platinum.ui.battle import run_trainer_battle
                        
                        outcome = run_trainer_battle(next_trainer_id, ctx)
                        
                        # Set appropriate flags
                        if outcome == 'PLAYER_WIN':
                            ctx.set_flag(next_trainer_flag)
                            ctx.set_flag(f"trainer_{next_trainer_id}_defeated")
                            ctx.set_flag(f"battle_{next_trainer_id}_won")
                        elif outcome == 'PLAYER_LOSS':
                            ctx.set_flag(f"battle_{next_trainer_id}_lost")
                        
                        # Don't return - continue the overworld loop to stay on current route
                        needs_pause = False
                    except Exception as e:
                        _show_text_block(f"Error in auto-battle: {e}")
                        # Don't return - continue the overworld loop
                        needs_pause = False
            else:
                # All trainers defeated or not route 202 - proceed with normal move
                if action.target:
                    try:
                        ctx.state.location = action.target
                        # Fire enter_map trigger for event scripts (e.g., lake shore cutscene)
                        try:
                            ctx.events.dispatch_trigger({"type": "enter_map", "value": ctx.state.location})
                        except Exception:
                            pass
                    except Exception:
                        pass
                else:
                    print("Destination not implemented yet.")
        elif action.type == 'exit':
            # On exit, stop music cleanly
            try:
                audio.fadeout(500)
            except Exception:
                pass
            return
        else:
            _show_text_block(f"[overworld] Unknown action type {action.type}")
            needs_pause = False
        # No trailing input here; branches handle their own wait via _show_text_block


def _open_pause_menu(ctx) -> None:
    """Pause menu opened via B in overworld. Provides Pokedex, Pokemon, Bag,
    Trainer Card, Town Map (WIP), Options (WIP), Save and Exit. B or Esc closes.
    """
    while True:
        # Build menu items based on what player has unlocked
        menu_items = []
        
        # Only show Pokedex if player has received it from Professor Rowan
        if ctx.has_flag('pokedex_received'):
            menu_items.append(("Pokedex", "pokedex"))
        
        menu_items.extend([
            ("Pokemon", "pokemon"),
            ("Bag", "bag"),
            ("Trainer Card", "trainer"),
            ("Town Map", "map"),
            ("Options", "options"),
            ("Save and Exit", "save_exit"),
            ("Return", "return"),
        ])
        
        choice = select_menu(
            "MENU",
            menu_items,
            footer="↑/↓ or W/S to move • Enter to select • B/Esc to return"
        )
        if choice in (None, "__b__", "return"):
            return
        if choice == "pokedex":
            _menu_pokedex(ctx)
        elif choice == "pokemon":
            _menu_pokemon(ctx)
        elif choice == "bag":
            _menu_bag(ctx)
        elif choice == "trainer":
            _menu_trainer_card(ctx)
        elif choice == "map":
            _menu_town_map(ctx)
        elif choice == "options":
            try:
                from platinum.system.settings import Settings as _S
                options_submenu(_S.load())
            except Exception:
                pass
        elif choice == "save_exit":
            _menu_save_and_exit(ctx)


def _menu_pokedex(ctx) -> None:
    # Simple text list of seen/caught species names from save state
    seen = getattr(ctx.state, 'pokedex_seen', [])
    caught = set(getattr(ctx.state, 'pokedex_caught', []))
    items: list[tuple[str,str]] = []
    for sid in seen:
        name = str(sid).replace('_', ' ').title()
        suffix = " (caught)" if sid in caught else ""
        items.append((name + suffix, sid))
    if not items:
        items = [("No data. See Pokemon in the wild to register.", "ok")]
    items.append(("Return", "return"))
    while True:
        choice = select_menu("POKEDEX", items)
        if choice in (None, "__b__", "return"):
            return


def _menu_pokemon(ctx) -> None:
    # List party with name, status, HP bar; allow swapping indices
    def _party_menu_items():
        out: list[tuple[str,str]] = []
        try:
            from platinum.ui.battle import _hp_bar  # reuse renderer
        except Exception:
            _hp_bar = lambda cur, m, width=24: f"HP {cur}/{m}"
        for idx, pm in enumerate(getattr(ctx.state, 'party', [])):
            status = f" [{pm.status}]" if getattr(pm, 'status', None) else ""
            hp_str = _hp_bar(getattr(pm, 'hp', 0), getattr(pm, 'max_hp', getattr(pm, 'hp', 0)))
            label = f"{idx+1}. {pm.species.title()} Lv{pm.level}{status} | {hp_str}"
            out.append((label, str(idx)))
        out.append(("Return", "return"))
        return out
    select_idx: Optional[int] = None
    while True:
        choice = select_menu("POKEMON", _party_menu_items())
        if choice in (None, "__b__", "return"):
            return
        try:
            idx = int(choice)
        except ValueError:
            continue
        if select_idx is None:
            # First selection; prompt to select a second to swap
            select_idx = idx
            tw.type_out(f"Selected slot {idx+1}. Choose another to swap or press B to cancel.", Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
            tw.wait_for_continue()
        else:
            j = idx
            party = ctx.state.party
            if 0 <= select_idx < len(party) and 0 <= j < len(party) and select_idx != j:
                party[select_idx], party[j] = party[j], party[select_idx]
                tw.type_out(f"Swapped positions {select_idx+1} and {j+1}.", Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
                tw.wait_for_continue()
            select_idx = None


def _menu_bag(ctx) -> None:
    """Structured bag menu with pockets, similar to battle bag."""
    # Initialize Rich console
    console = Console()
    
    inv = getattr(ctx.state, 'inventory', {}) or {}
    
    def _fmt(name: str, count: int) -> str:
        return f"{name.replace('-', ' ').title()} ×{count}"
    
    # Define pocket categories (same as battle)
    pockets = [
        ("Items", lambda n: n in {"repel", "escape-rope", "x-attack", "x-defend"}),
        ("Medicine", lambda n: n in {"potion", "super-potion", "antidote", "paralyze-heal", "ether"}),
        ("Poke Balls", lambda n: n.endswith("ball")),
        ("TMs & HMs", lambda n: n.startswith("tm") or n.startswith("hm")),
        ("Berries", lambda n: n.endswith("berry")),
        ("Key Items", lambda n: n in {"town-map", "old-rod", "works-key"}),
    ]
    
    while True:
        # Create pocket menu items
        pocket_items = [MenuItem(p[0], p[0]) for p in pockets]
        pocket_items.append(MenuItem("Cancel", "__cancel__"))
        
        # Custom full render function for overworld bag
        def render_overworld_bag_ui():
            console.clear()
            
            # Add some top spacing
            console.print("\n")
            
            # Title
            title_panel = Panel(
                "[bold bright_cyan]BAG[/bold bright_cyan]",
                style="bright_white",
                box=ROUNDED,
                width=40
            )
            console.print(Align.center(title_panel))
            console.print()
            
            # Create beautiful pocket selection menu
            from platinum.ui.menu_nav import get_menu_color
            menu_color = get_menu_color()
            
            menu_table = Table(
                title=f"[bold {menu_color}]CHOOSE POCKET[/bold {menu_color}]",
                box=ROUNDED,
                show_header=False,
                style="bright_white",
                title_style=f"bold {menu_color}",
                width=60
            )
            
            menu_table.add_column("Option", style="bright_white", justify="left")
            
            for i, item in enumerate(pocket_items):
                # Create styled menu item with arrow pointer
                if i == pocket_menu.index:
                    prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                    suffix = f"[/{menu_color}]"
                else:
                    prefix = "  [bright_white]"
                    suffix = "[/bright_white]"
                
                full_label = f"{prefix}{item.label}{suffix}"
                menu_table.add_row(full_label)
            
            # Display the menu
            console.print(Align.center(menu_table))
            
            # Footer
            footer_panel = Panel(
                "↑/↓ W/S • Enter to open • Esc to go back",
                style="dim bright_white",
                box=ROUNDED
            )
            console.print(footer_panel)
        
        pocket_menu = Menu(
            "Choose Pocket",
            pocket_items,
            allow_escape=True,
            footer="↑/↓ W/S • Enter to open • Esc to go back",
            full_render=render_overworld_bag_ui,
        )
        psel = pocket_menu.run()
        
        if not psel or psel == "__cancel__":
            return
        
        pocket = next((p for p in pockets if p[0]==psel), None)
        if not pocket:
            continue
        
        # Build item list for the chosen pocket
        filt = pocket[1]
        items_in_pocket = [(n,c) for n,c in sorted(inv.items()) if c>0 and filt(n)]
        
        if not items_in_pocket:
            console.clear()
            console.print(f"\n[yellow]No items in {psel} pocket.[/yellow]")
            console.print("\nPress Enter to continue...")
            input()
            continue
        
        # Create item menu
        item_items = [MenuItem(f"{_fmt(n,c)}", n) for n, c in items_in_pocket]
        item_items.append(MenuItem("Cancel", "__cancel__"))
        
        # Custom full render function for items
        def render_overworld_item_ui():
            console.clear()
            
            # Add some top spacing  
            console.print("\n")
            
            # Title
            title_panel = Panel(
                f"[bold bright_cyan]{(psel or 'BAG').upper()}[/bold bright_cyan]",
                style="bright_white",
                box=ROUNDED,
                width=40
            )
            console.print(Align.center(title_panel))
            console.print()
            
            # Create item selection menu
            from platinum.ui.menu_nav import get_menu_color
            menu_color = get_menu_color()
            
            menu_table = Table(
                title=f"[bold {menu_color}]{(psel or 'ITEMS').upper()}[/bold {menu_color}]",
                box=ROUNDED,
                show_header=False,
                style="bright_white",
                title_style=f"bold {menu_color}",
                width=60
            )
            
            menu_table.add_column("Item", style="bright_white", justify="left")
            
            for i, item in enumerate(item_items):
                # Create styled menu item with arrow pointer
                if i == item_menu.index:
                    prefix = f"[{menu_color}]►[/{menu_color}] [{menu_color}]"
                    suffix = f"[/{menu_color}]"
                else:
                    prefix = "  [bright_white]"
                    suffix = "[/bright_white]"
                
                full_label = f"{prefix}{item.label}{suffix}"
                menu_table.add_row(full_label)
            
            # Display the menu
            console.print(Align.center(menu_table))
            
            # Footer
            footer_panel = Panel(
                "↑/↓ W/S • Enter to select • Esc to go back",
                style="dim bright_white",
                box=ROUNDED
            )
            console.print(footer_panel)
        
        item_menu = Menu(
            f"{psel}",
            item_items,
            allow_escape=True,
            footer="↑/↓ W/S • Enter to select • Esc to go back",
            full_render=render_overworld_item_ui,
        )
        sel = item_menu.run()
        
        if not sel or sel == "__cancel__":
            continue
        
        # For now, just show item info (can add usage later)
        console.clear()
        console.print(f"\n[green]Selected: {sel.replace('-', ' ').title()}[/green]")
        console.print(f"[yellow]Count: {inv.get(sel, 0)}[/yellow]")
        console.print(f"\n[dim]Item usage in overworld coming soon![/dim]")
        console.print("\nPress Enter to continue...")
        input()
        # Go back to item selection


def _menu_trainer_card(ctx) -> None:
    # Show playtime in minutes, money, and badges
    try:
        ctx._accumulate_play_time()
    except Exception:
        pass
    minutes = int(getattr(ctx.state, 'play_time_seconds', 0) // 60)
    money = int(getattr(ctx.state, 'money', 0))
    badges = getattr(ctx.state, 'badges', []) or []
    lines = [
        f"Trainer: {getattr(ctx.state, 'player_name', 'PLAYER')}",
        f"Play Time: {minutes} min",
        f"Money: ₽{money}",
        f"Badges: {len(badges)}",
    ]
    _show_block = "\n".join(lines)
    try:
        tw.clear_screen()
    except Exception:
        pass
    tw.type_out(_show_block, Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
    tw.wait_for_continue()


def _menu_town_map(ctx) -> None:
    # WIP simple text
    try:
        tw.clear_screen()
    except Exception:
        pass
    tw.type_out("Town Map is under construction.", Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
    tw.wait_for_continue()


def _menu_save_and_exit(ctx) -> None:
    # Save, then exit to main menu (stop music)
    try:
        ctx.state.flags = sorted(ctx.flags)
    except Exception:
        pass
    try:
        ctx._accumulate_play_time()
    except Exception:
        pass
    try:
        path = save_game(ctx.state)
        delete_temp()
        tw.type_out("Game saved.", Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
        print(f"Saved to {path.name}")
        tw.wait_for_continue()
    except Exception:
        tw.type_out("Save failed.", Settings.load().data.text_speed if hasattr(Settings.load(), 'data') else 2)
        tw.wait_for_continue()
    try:
        audio.fadeout(500)
    except Exception:
        pass
    # Exit entire overworld loop by raising SystemExit-like flow
    raise SystemExit(0)
