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
from platinum.ui.menu_nav import select_menu

LOCATIONS_DIR = Path("assets/locations")
INDEX_FILE = LOCATIONS_DIR / "overworld.json"  # legacy single-file or index (contains root_id)

@dataclass
class Action:
    label: str
    type: str
    target: Optional[str] = None
    text: Optional[str] = None
    dialogue_key: Optional[str] = None
    fallback_text: Optional[str] = None
    set_flag: Optional[str] = None
    zone: Optional[str] = None
    method: Optional[str] = None

@dataclass
class LocationNode:
    id: str
    name: str
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
            loc = LocationNode(id=data['id'], name=data.get('name', data['id']), actions=actions, children=[])
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
            ln = LocationNode(id=node['id'], name=node.get('name', node['id']), actions=actions, children=children)
            return ln
        root = build(data)
        nodes = root.collect()
        root_id = root.id
        return (root, nodes)

    root = nodes.get(root_id) if root_id else None
    return (root, nodes)


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
    
    while True:
        node = all_nodes.get(ctx.state.location)
        if not node:
            print("[overworld] Unknown location; exiting.")
            return
            
        # Announce location when first entering or changing locations
        if last_announced_location != ctx.state.location:
            print(f"\n({node.name})")
            print("--------------------")  # Divider for visual clarity
            last_announced_location = ctx.state.location
            
        # Build menu
        menu_items = [(a.label, str(i)) for i,a in enumerate(node.actions)]
        title = f"LOCATION: {node.name}"
        choice = select_menu(title, menu_items, footer="↑/↓ or W/S • Enter select • Esc=Exit")
        if choice is None:
            return
        try:
            idx = int(choice)
        except ValueError:
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
                    # Location change announcement handled in next loop iteration
                    
                    # Fire enter_map trigger for event scripts (e.g., lake shore cutscene)
                    try:
                        ctx.events.dispatch_trigger({"type": "enter_map", "value": ctx.state.location})
                    except Exception:
                        pass
            else:
                print("Destination not implemented yet.")
        elif action.type == 'inspect':
            if action.text:
                print(action.text)
                needs_pause = True
            if action.set_flag:
                ctx.set_flag(action.set_flag)
        elif action.type == 'dialogue':
            # If this dialogue sets a flag and it's already set, treat it as a post-intro repeat -> fallback
            if action.set_flag and ctx.has_flag(action.set_flag):
                if action.fallback_text:
                    print(action.fallback_text)
                    needs_pause = True
                else:
                    # Nothing new to say
                    pass
            else:
                if action.dialogue_key:
                    ctx.dialogue.show(action.dialogue_key)
                    needs_pause = True
                elif action.fallback_text:
                    print(action.fallback_text)
                    needs_pause = True
                if action.set_flag and not ctx.has_flag(action.set_flag):
                    ctx.set_flag(action.set_flag)
        elif action.type == 'briefcase':
            # Lake briefcase interaction gating
            if not ctx.has_flag('rival_introduced'):
                print("You shouldn't mess with this yet—maybe talk with your friend first.")
                needs_pause = True
            elif ctx.has_flag('starter_chosen'):
                print("The briefcase is empty now. Your adventure has begun.")
                needs_pause = True
            elif ctx.has_flag('lake_plan_formed'):
                # Plan already formed; allow retrigger of event chain if starter not chosen
                print(action.text or "The briefcase sits here, waiting.")
                ctx.events.dispatch_trigger({"type": "flag_set", "value": "lake_plan_formed"})
                needs_pause = True
            else:
                # First time: form plan + trigger
                print(action.text or "A professor's briefcase... It looks forgotten.")
                ctx.set_flag('lake_plan_formed')
                needs_pause = True
        elif action.type == 'tall_grass_attempt':
            # Attempt to enter grass: if no starter, trigger intercept; else allow future encounter actions
            if ctx.has_flag('starter_chosen'):
                print("You step into the tall grass...")
                needs_pause = True
            else:
                ctx.events.dispatch_trigger({"type": "attempt_grass_entry", "value": action.target or action.text or 'route_201'})
        elif action.type == 'encounter':
            if not ctx.state.party:
                print("You have no Pokémon—Professor Rowan would not approve entering the grass.")
                needs_pause = True
            elif not ctx.has_flag('starter_chosen'):
                print("You hesitate—maybe talk to the Professor first.")
                needs_pause = True
            else:
                print("(Encounter system placeholder: wild battle would start.)")
                needs_pause = True
        elif action.type == 'exit':
            return
        else:
            print(f"[overworld] Unknown action type {action.type}")
        if needs_pause:
            try:
                input("Press Enter to continue...")
            except EOFError:
                pass
