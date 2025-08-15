#!/usr/bin/env bash
set -euo pipefail

# Create directories
mkdir -p schema
mkdir -p assets/dialogue/en/core
mkdir -p assets/dialogue/en/variants
mkdir -p assets/dialogue/en/meta
mkdir -p assets/battle_configs/rival
mkdir -p assets/events/main
mkdir -p assets/events/galactic
mkdir -p src/platinum/events
mkdir -p src/platinum/ui
mkdir -p src/platinum/core
mkdir -p src/platinum/inventory
mkdir -p src/platinum/config
mkdir -p tests/unit

# ---- Write files ----
cat > schema/event.schema.json <<'EOF'
{ "$schema":"https://json-schema.org/draft/2020-12/schema", "title":"Platinum Event", "type":"object",
  "required":["id","category","triggers","script"],
  "properties":{
    "id":{"type":"string","pattern":"^[a-z0-9_.-]+$"},
    "category":{"type":"string","enum":["main","gym","galactic","rival","system","optional","legend"]},
    "description":{"type":"string"},
    "phase":{"type":"integer","minimum":0},
    "prerequisites":{"type":"array","items":{"type":"string"},"uniqueItems":true},
    "triggers":{"type":"array","minItems":1,"items":{"type":"object","required":["type"],
      "properties":{"type":{"type":"string"},"location":{"type":"string"},"npc_id":{"type":"string"},
        "group_id":{"type":"string"},"map":{"type":"string"},"tile":{"type":"array","items":{"type":"integer"},"minItems":2,"maxItems":2},
        "name":{"type":"string"}}, "additionalProperties":true}},
    "once":{"type":"boolean","default":true},
    "set_flags":{"type":"array","items":{"type":"string"},"uniqueItems":true},
    "clear_flags":{"type":"array","items":{"type":"string"},"uniqueItems":true},
    "reward":{"type":"object"},
    "script":{"type":"array","items":{"type":"object","required":["cmd"],"properties":{"cmd":{"type":"string"}},"additionalProperties":true}},
    "next_hints":{"type":"array","items":{"type":"object","required":["text_id"],
      "properties":{"text_id":{"type":"string"},"conditions":{"type":"array","items":{"type":"string"}}}}}
  },
  "additionalProperties":false }
EOF

cat > assets/dialogue/en/characters.json <<'EOF'
{
  "player":"Player","barry":"Barry","rowan":"Professor Rowan","dawn":"Dawn","lucas":"Lucas",
  "mom_player":"Mom","mom_rival":"Barry's Mom","cynthia":"Cynthia","looker":"Looker",
  "mars":"Commander Mars","jupiter":"Commander Jupiter","saturn":"Commander Saturn",
  "cyrus":"Cyrus","cycle_shop_owner":"Cycle Shop Manager","gardenia":"Gardenia",
  "roark":"Roark","fantina":"Fantina","maylene":"Maylene","wake":"Crasher Wake",
  "byron":"Byron","candice":"Candice","galactic_grunt":"Team Galactic Grunt",
  "scientist_hostage":"Windworks Scientist","announcer":"Announcer","narration":"Narration"
}
EOF

# Core dialogue packs (phase0, phase1, phase2)
cat > assets/dialogue/en/core/phase0_intro.json <<'EOF'
{ "_comment":"Phase 0 Intro",
  "intro.tv.program":{"base":"A broadcast featuring Professor Rowan discusses new ecological studies in Sinnoh.",
    "expanded":"The TV host chats with Professor Rowan about Pokémon adaptation. Rowan’s calm baritone hints at decades of field work. Barry would never sit through this—yet here you are.",
    "alt":["Professor Rowan appears on screen, fielding a question about balancing research and trainer journeys.",
      "A calm interview: Rowan speaks of migration patterns while a banner scrolls: 'Sinnoh League Season Opens Soon!'"]},
  "barry.enters.player.house":{"base":"Barry bursts in, buzzing with energy.",
    "expanded":"With the force of an unscheduled thunderbolt, Barry slams the door open. 'If Rowan’s back, we go NOW! Ten million fine if you’re late!'",
    "alt":["Barry rushes in mid-sentence about timing splits.","Barry nearly trips over your rug, recovers, and declares a departure race."]},
  "route201.pre.grass.stop":{"base":"You edge toward tall grass when a firm voice halts you.",
    "expanded":"Just as Barry leans forward like a dive start, a measured voice slices the morning air: 'Reckless curiosity invites preventable harm.' Rowan stands, imposing yet oddly approving.",
    "alt":["Rowan: 'Impatience is common. Survival afterward is less common without preparation.'",
      "Rowan folds his arms, eyes flicking between you and Barry: 'An impulsive sprint into tall grass—classic.'"]},
  "rowan.offer.starters":{"base":"Rowan presents three Poké Balls.",
    "expanded":"Rowan sets the case down; three capsules gleam. 'Consider temperament—yours and theirs. Partnership is chosen, not imposed.'",
    "alt":["'Inside: steadfast leaf, blazing spirit, resilient tide. Decide with intent.'","Dawn (quietly): 'They’ve been kept healthy—each is eager.'"]},
  "starter.chosen.reaction":{"base":"You take the Poké Ball. A new journey begins.",
    "expanded":"The Poké Ball’s seam warms faintly—acceptance pulsing. Barry sizes up your choice. Determination sparks between you.",
    "alt":["A subtle nod from Rowan: 'Responsibility travels with that choice.'","Dawn smiles: 'Treat it well; it’ll answer in battle.'"]},
  "barry.first.challenge":{"base":"Barry challenges you immediately.",
    "expanded":"Barry pivots so fast dust lifts. 'Test run! No data, no growth!' He snaps a stance like he practiced in the mirror.",
    "alt":["'Battle now—optimize later!' Barry grins.","Barry: 'If we analyze right away, we iterate faster!'"]},
  "battle.rival.1.after.win":{"base":"Barry concedes, still fired up.",
    "expanded":"'Okay okay— early variance! RNG or skill? We rematch soon.' He points dramatically, already planning build paths.",
    "alt":["Barry: 'Not salty, just motivated.'","'Your starter’s synergy is promising—respect.'"]},
  "battle.rival.1.after.loss":{"base":"Barry celebrates his quick win.",
    "expanded":"Barry pumps a fist. 'Momentum matters! Adapt—we both scale from here.'",
    "alt":["'Openings exploited! Replay soon.'","Barry: 'Your risk curve was greedy. Love it. Fix it.'"]},
  "return.home.mom.running.shoes":{"base":"Mom provides Running Shoes.",
    "expanded":"Your mother kneels to check laces like you’re still half your size. 'Speed helps—but rest helps more.' She hands over the Running Shoes.",
    "alt":["'Take these. Don’t skip meals chasing dreams.'","Mom: 'Write when you can. Or at least heal your partner regularly.'"]}
}
EOF

cat > assets/dialogue/en/core/phase1_early_routes.json <<'EOF'
{ "_comment":"Phase 1",
  "sandgem.dawn.greets":{"base":"Dawn waits outside, ready to escort you.",
    "expanded":"Dawn stands poised, clipboard tucked under arm. 'Professor wants baseline readings—this way.' Her partner shifts its weight, relaxed.",
    "alt":["'You made good time. Lab’s prepped.'","Dawn: 'Let’s register your partner formally.'"]},
  "rowan.lab.evaluation":{"base":"Rowan evaluates your bond.",
    "expanded":"Rowan studies subtle posture alignment between you and your starter. 'Mutual readiness evident. Suitable for longitudinal field data acquisition.'",
    "alt":["'Trust curve forming faster than median.'","Rowan: 'Continue reinforcing positive battle feedback.'"]},
  "rowan.gives.pokedex":{"base":"You receive the Pokédex.",
    "expanded":"Rowan hands over a calibrated unit. 'Catalog presence first, custody second. Every record sharpens understanding beyond anecdote.'",
    "alt":["'Data integrity depends on observation discipline.'","Rowan: 'You extend our reach—responsibly, I expect.'"]},
  "barrys.mom.parcel":{"base":"Barry's Mom entrusts you with a Parcel.",
    "expanded":"Barry’s Mom exhales a half-laugh. 'He left mid-sentence again—please get this to him. Maybe a map slows him down.'",
    "alt":["'He forgot supplies—again. Help him out.'","She presses a neatly wrapped case into your hands."]},
  "tutorial.catching.preface":{"base":"Dawn offers a catching demonstration.",
    "expanded":"Dawn: 'HP thresholds plus a status condition raise capture probability. Watch the sequencing—chip, status, ball.'",
    "alt":["'Observe variance; partial RNG management is strategic.'","Dawn: 'Over-weakening risks accidental KO. Balance.'"]},
  "tutorial.catching.after":{"base":"You receive Poké Balls.",
    "expanded":"Dawn hands over a bundle. 'Consider type coverage early. Don’t over-invest in similar roles before second Gym.'",
    "alt":["'Here—seed capital for your roster.'","Dawn: 'Adapt move sets as stats differentiate.'"]},
  "jubilife.looker.intro":{"base":"A stranger watches from a lamp post.",
    "expanded":"The man awkwardly feigns blending with a lamp post. 'I am Looker—international investigation liaison. Pattern anomalies interest me. Remain observant.'",
    "alt":["Looker: 'Discretion is my brand. Usually.'","'If you spot suspicious energy logistics, report.'"]},
  "poketch.clown.pitch":{"base":"Promoter urges you to find three clowns.",
    "expanded":"Promoter: 'Gamified outreach! Answer trivial knowledge, earn coupons—redeem for a Pokétch. Engagement strategy!'",
    "alt":["'Collect three correct stamps; convergence yields reward.'","Promoter winks: 'User acquisition through interactive trivia.'"]},
  "poketch.awarded":{"base":"You receive the Pokétch.",
    "expanded":"The device’s display blinks to life cycling basic modules—time, steps, party health. 'Iterative app rollout occurs with milestones—check back after key victories.'",
    "alt":["'Your wrist hardware just leveled up.'","Promoter: 'Expect new modules at odd badge counts.'"]}
}
EOF

cat > assets/dialogue/en/core/phase2_windworks.json <<'EOF'
{ "_comment":"Phase 2 Windworks",
  "floaroma.entry":{"base":"Floral scent rides the wind.",
    "expanded":"Color bands ripple across the meadow edges—petals swirling like soft confetti. Calm before industrial tension nearby.",
    "alt":["A layered perfume saturates the breeze.","Petals catch in your partner’s fur momentarily."]},
  "meadow.grunts.harassing":{"base":"Two grunts pressure a man for honey.",
    "expanded":"Grunt A: 'Supply chain optimization—we requisition your honey stock.' The keeper clutches jars, voice shaking.",
    "alt":["Grunt B: 'Hand it over—corporate cosmic progress demands inputs.'","'Stand aside—our projection models require this commodity.'"]},
  "works.key.recovered":{"base":"You obtain the Works Key.",
    "expanded":"Both grunts scramble—one drops the key. Metallic clink echoes; leverage shifts instantly.",
    "alt":["The key spins in moss—abandoned tactical asset.","'Operational security failure—withdraw!'"]},
  "windworks.entry.unlocked":{"base":"The lock disengages.",
    "expanded":"Panel light flips from amber to green; fans within deepen their hum—a regulated energy core awaiting intrusion.",
    "alt":["A soft hydraulic hiss signals access.","Door logic cycles: authentication bypassed."]},
  "mars.pre.battle":{"base":"Mars challenges you.",
    "expanded":"Mars twirls a strand of crimson hair. 'You're the variable skewing my capture pipeline? Control test: let’s measure your ceiling.'",
    "alt":["'Interference metrics rising. Neutralize engagement.'","Mars: 'I’ll log this thrashing as R&D overhead.'"]},
  "mars.post.battle":{"base":"Mars retreats, vowing escalation.",
    "expanded":"Mars scowls—analysis overlay in her eyes. 'Data gathered. Iteration will exceed this friction next deployment.'",
    "alt":["'Fine—statistically insignificant setback.'","Mars: 'Galactic scope moves beyond this turbine shack.'"]},
  "windworks.hostage.freedom":{"base":"The hostage thanks you.",
    "expanded":"Scientist rubs wrists where restraints etched faint marks. 'They probed for grid load patterns. Safeguards held—thanks to you.'",
    "alt":["'They wanted conversion ratios. I stalled.'","Scientist: 'I can resume maintenance safely now.'"]}
}
EOF

# Characters variants selector
cat > assets/dialogue/en/variants/selector_config.json <<'EOF'
{ "default_mode":"expanded",
  "modes":{
    "concise":{"fallback":"base"},
    "expanded":{"fallback":"expanded"},
    "alt":{"cycle":true}
  }
}
EOF

# Meta provenance
cat > assets/dialogue/en/meta/provenance.json <<'EOF'
{ "_comment":"Non-copyrighted paraphrased dialogue metadata",
  "philosophy":"Paraphrased expansions maintain tone & pacing; no verbatim source lines.",
  "review_status":{"phase0_intro":"draft_v1","phase1_early_routes":"draft_v1","phase2_windworks":"draft_v1"}
}
EOF

# Battle config
cat > assets/battle_configs/rival/rival_1.json <<'EOF'
{
  "id":"rival_1",
  "opponent_id":"TRAINER_RIVAL",
  "teams":[
    {"player_starter":"turtwig","enemy":[{"species":"chimchar","level":5,"moves":["scratch","leer"]}]},
    {"player_starter":"chimchar","enemy":[{"species":"piplup","level":5,"moves":["pound","growl"]}]},
    {"player_starter":"piplup","enemy":[{"species":"turtwig","level":5,"moves":["tackle","withdraw"]}]}
  ],
  "reward_money":300,
  "ai":"basic"
}
EOF

# Events
cat > assets/events/main/000_story_start.json <<'EOF'
{
  "id":"story.start","category":"main","phase":0,"prerequisites":[],
  "triggers":[{"type":"game_start"}],"once":true,"set_flags":["story.start"],
  "script":[{"cmd":"SHOW_TEXT","speaker":"narration","text_id":"intro.tv.program"}]
}
EOF

cat > assets/events/main/010_rival_initial_visit.json <<'EOF'
{
  "id":"story.rival_initial_visit","category":"main","phase":0,
  "prerequisites":["story.start","!story.rival_initial_visit"],
  "triggers":[{"type":"enter_location","location":"PLAYER_HOUSE_1F"}],
  "once":true,"set_flags":["story.rival_initial_visit"],
  "script":[{"cmd":"SHOW_TEXT","speaker":"barry","text_id":"barry.enters.player.house"}]
}
EOF

cat > assets/events/main/020_route201_attempt.json <<'EOF'
{
  "id":"story.route201_attempt","category":"main","phase":0,
  "prerequisites":["story.rival_initial_visit","!story.route201_attempt"],
  "triggers":[{"type":"enter_location","location":"ROUTE_201_EDGE"}],
  "once":true,"set_flags":["story.route201_attempt"],
  "script":[
    {"cmd":"SHOW_TEXT","speaker":"rowan","text_id":"route201.pre.grass.stop"},
    {"cmd":"CALL_EVENT","event_id":"story.starter_selection"}
  ]
}
EOF

cat > assets/events/main/030_starter_selection.json <<'EOF'
{
  "id":"story.starter_selection","category":"main","phase":0,
  "prerequisites":["story.route201_attempt","!story.received_starter"],
  "triggers":[{"type":"script_call","name":"invoke_starter_menu"}],
  "once":true,"set_flags":["story.received_starter"],
  "script":[
    {"cmd":"SHOW_TEXT","speaker":"rowan","text_id":"rowan.offer.starters"},
    {"cmd":"STARTER_CHOICE","choices":["turtwig","chimchar","piplup"],"assign_flag_prefix":"starter."},
    {"cmd":"SHOW_TEXT","speaker":"narration","text_id":"starter.chosen.reaction"},
    {"cmd":"SHOW_TEXT","speaker":"barry","text_id":"barry.first.challenge"},
    {"cmd":"START_BATTLE","battle_id":"rival_1","context":"initial"}
  ]
}
EOF

cat > assets/events/main/040_running_shoes.json <<'EOF'
{
  "id":"item.key.running_shoes","category":"main","phase":1,
  "prerequisites":["story.received_starter","!item.key.running_shoes"],
  "triggers":[{"type":"enter_location","location":"PLAYER_HOUSE_1F"}],
  "once":true,"set_flags":["item.key.running_shoes"],
  "script":[
    {"cmd":"SHOW_TEXT","speaker":"mom_player","text_id":"return.home.mom.running.shoes"},
    {"cmd":"GIVE_ITEM","item":"running_shoes"}
  ],
  "next_hints":[{"text_id":"hint_go_route201"}]
}
EOF

cat > assets/events/galactic/120_windworks_commander.json <<'EOF'
{
  "id":"galactic.windworks_cleared","category":"galactic","phase":3,
  "prerequisites":["item.key.works_key","!galactic.windworks_cleared"],
  "triggers":[{"type":"enter_location","location":"VALLEY_WINDWORKS_INTERIOR"}],
  "once":true,"set_flags":["galactic.windworks_cleared"],
  "script":[
    {"cmd":"SHOW_TEXT","speaker":"mars","text_id":"mars.pre.battle"},
    {"cmd":"START_BATTLE","battle_id":"commander_mars_1"},
    {"cmd":"SHOW_TEXT","speaker":"mars","text_id":"mars.post.battle"},
    {"cmd":"SHOW_TEXT","speaker":"scientist_hostage","text_id":"windworks.hostage.freedom"}
  ],
  "reward":{"items":[{"id":"honey","qty":1}],"spawn_unlocks":["drifloon_friday"]}
}
EOF

# Python support files

cat > src/platinum/events/characters.py <<'EOF'
import json
from pathlib import Path
CHAR_PATH = Path("assets/dialogue/en/characters.json")
class CharacterNames:
    def __init__(self):
        self._map = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    def display(self, key: str) -> str:
        return self._map.get(key, key)
characters = CharacterNames()
EOF

cat > src/platinum/ui/dialogue_manager.py <<'EOF'
import json, random
from pathlib import Path
from typing import Dict, Any
class DialogueManager:
    def __init__(self, lang_dir: str = "assets/dialogue/en", mode: str = "expanded"):
        self.lang_dir = Path(lang_dir)
        self.mode = mode
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()
        cfg_path = self.lang_dir / "variants" / "selector_config.json"
        self.selector_cfg = {}
        if cfg_path.exists():
            self.selector_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    def _load_all(self):
        for p in self.lang_dir.rglob("*.json"):
            if p.name in ("characters.json","selector_config.json"):
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            for key,val in data.items():
                if key.startswith("_"):
                    continue
                self._cache[key]=val
    def set_mode(self, mode: str):
        self.mode = mode
    def resolve(self, text_id: str) -> str:
        entry = self._cache.get(text_id)
        if not entry:
            return f"[missing:{text_id}]"
        target_mode = self.mode
        variant = None
        if target_mode in entry:
            variant = entry[target_mode]
        elif target_mode == "alt" and "alt" in entry:
            pool = entry["alt"]
            if isinstance(pool,list) and pool:
                variant = random.choice(pool)
        if variant is None:
            if "expanded" in entry: variant = entry["expanded"]
            elif "base" in entry: variant = entry["base"]
            else:
                alt = entry.get("alt")
                if isinstance(alt,list) and alt: variant = alt[0]
                else: variant = "[no text]"
        return variant
EOF

cat > src/platinum/events/types.py <<'EOF'
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
@dataclass
class Trigger:
    type: str
    location: str | None = None
    npc_id: str | None = None
    group_id: str | None = None
    map: str | None = None
    tile: tuple[int,int] | None = None
    name: str | None = None
    raw: Dict[str,Any] = field(default_factory=dict)
@dataclass
class ScriptCommand:
    cmd: str
    args: Dict[str, Any]
@dataclass
class EventDef:
    id: str
    category: str
    phase: int
    prerequisites: List[str]
    triggers: List[Trigger]
    script: List[ScriptCommand]
    once: bool = True
    set_flags: List[str] = field(default_factory=list)
    clear_flags: List[str] = field(default_factory=list)
    reward: Dict[str, Any] = field(default_factory=dict)
    next_hints: List[Dict[str, Any]] = field(default_factory=list)
EOF

cat > src/platinum/events/registry.py <<'EOF'
from __future__ import annotations
from typing import Dict, List
from .types import EventDef
class EventRegistry:
    def __init__(self):
        self._events: Dict[str, EventDef] = {}
        self._triggers_index: Dict[str, List[EventDef]] = {}
    def add(self, event: EventDef):
        if event.id in self._events:
            raise ValueError(f"Duplicate event id {event.id}")
        self._events[event.id] = event
        for trig in event.triggers:
            key = trig.type
            self._triggers_index.setdefault(key, []).append(event)
    def by_id(self, event_id: str) -> EventDef | None:
        return self._events.get(event_id)
    def candidates_for_trigger(self, trig_type: str) -> List[EventDef]:
        return self._triggers_index.get(trig_type, [])
    def all(self) -> List[EventDef]:
        return list(self._events.values())
EOF

cat > src/platinum/events/loader.py <<'EOF'
import json
from pathlib import Path
from jsonschema import validate
from .types import EventDef, Trigger, ScriptCommand
from .registry import EventRegistry
SCHEMA_PATH = Path("schema/event.schema.json")
EVENTS_ROOT = Path("assets/events")
def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
def coerce_event(obj: dict) -> EventDef:
    triggers = []
    for t in obj["triggers"]:
        t_copy = dict(t)
        t_type = t_copy.pop("type")
        triggers.append(Trigger(type=t_type, raw=t, **t_copy))
    script_cmds = []
    for c in obj["script"]:
        c_copy = dict(c)
        cmd = c_copy.pop("cmd")
        script_cmds.append(ScriptCommand(cmd=cmd, args=c_copy))
    return EventDef(
        id=obj["id"], category=obj["category"], phase=obj.get("phase",0),
        prerequisites=obj.get("prerequisites", []), triggers=triggers,
        script=script_cmds, once=obj.get("once", True),
        set_flags=obj.get("set_flags", []), clear_flags=obj.get("clear_flags", []),
        reward=obj.get("reward", {}), next_hints=obj.get("next_hints", [])
    )
def load_events(registry: EventRegistry | None = None) -> EventRegistry:
    schema = load_schema()
    registry = registry or EventRegistry()
    for path in EVENTS_ROOT.rglob("*.json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        validate(obj, schema)
        evt = coerce_event(obj)
        registry.add(evt)
    return registry
if __name__ == "__main__":
    reg = load_events()
    print(f"Loaded {len(reg.all())} events.")
EOF

cat > src/platinum/events/characters/__init__.py <<'EOF'
# Namespace package if needed later
EOF

cat > src/platinum/events/scripts.py <<'EOF'
from .characters import characters
from platinum.ui.dialogue_manager import DialogueManager  # runtime injection expected
def cmd_SHOW_TEXT(ctx, **kwargs):
    text_id = kwargs.get("text_id")
    speaker_key = kwargs.get("speaker","narration")
    speaker = characters.display(speaker_key)
    line = ctx.dialogue.resolve(text_id)
    ctx.ui.show_dialogue(speaker, line)
def cmd_GIVE_ITEM(ctx, **kwargs):
    item = kwargs["item"]; qty = kwargs.get("qty",1)
    ctx.inventory.add(item, qty)
    ctx.log(f"Received {item} x{qty}")
def cmd_SET_FLAG(ctx, **kwargs):
    flag = kwargs["flag"]; ctx.flags.set(flag, True)
def cmd_START_BATTLE(ctx, **kwargs):
    battle_id = kwargs["battle_id"]
    ctx.battle_manager.start(battle_id, context=kwargs.get("context"))
def cmd_STARTER_CHOICE(ctx, **kwargs):
    choices = kwargs["choices"]
    prefix = kwargs.get("assign_flag_prefix","starter.")
    chosen = ctx.ui.choose_starter(choices)
    ctx.flags.set(prefix+chosen, True)
    ctx.flags.set("player.starter", chosen)
def cmd_CALL_EVENT(ctx, **kwargs):
    event_id = kwargs["event_id"]; ctx.event_engine.invoke(event_id)
COMMAND_HANDLERS = {
    "SHOW_TEXT": cmd_SHOW_TEXT,
    "GIVE_ITEM": cmd_GIVE_ITEM,
    "SET_FLAG": cmd_SET_FLAG,
    "START_BATTLE": cmd_START_BATTLE,
    "STARTER_CHOICE": cmd_STARTER_CHOICE,
    "CALL_EVENT": cmd_CALL_EVENT
}
def execute_script(ctx, script):
    for command in script:
        handler = COMMAND_HANDLERS.get(command.cmd)
        if not handler:
            ctx.log(f"[WARN] Unknown command {command.cmd}")
            continue
        handler(ctx, **command.args)
EOF

cat > src/platinum/events/engine.py <<'EOF'
from .scripts import execute_script
class EventEngine:
    def __init__(self, registry, ctx):
        self.registry = registry
        self.ctx = ctx
        self.executed_once = set()
    def handle_trigger(self, trig_type: str, **payload):
        for evt in self.registry.candidates_for_trigger(trig_type):
            if not self._eligible(evt):
                continue
            execute_script(self.ctx, evt.script)
            for f in evt.set_flags: self.ctx.flags.set(f, True)
            for f in evt.clear_flags: self.ctx.flags.set(f, False)
            if evt.once: self.executed_once.add(evt.id)
    def invoke(self, event_id: str):
        evt = self.registry.by_id(event_id)
        if evt and self._eligible(evt):
            execute_script(self.ctx, evt.script)
            for f in evt.set_flags: self.ctx.flags.set(f, True)
            for f in evt.clear_flags: self.ctx.flags.set(f, False)
            if evt.once: self.executed_once.add(evt.id)
    def _eligible(self, evt):
        if evt.once and evt.id in self.executed_once:
            return False
        for p in evt.prerequisites:
            if p.startswith("!"):
                if self.ctx.flags.get(p[1:]): return False
            else:
                if not self.ctx.flags.get(p): return False
        return True
EOF

cat > src/platinum/events/__init__.py <<'EOF'
from .loader import load_events
from .engine import EventEngine
from .registry import EventRegistry
EOF

cat > src/platinum/config/flags.py <<'EOF'
class FlagStore:
    def __init__(self): self._flags = {}
    def set(self, flag: str, value: bool=True): self._flags[flag]=value
    def get(self, flag: str) -> bool: return self._flags.get(flag, False)
    def snapshot(self): return dict(self._flags)
EOF

cat > src/platinum/inventory/__init__.py <<'EOF'
class Inventory:
    def __init__(self): self._items = {}
    def add(self, item_id: str, qty: int=1):
        self._items[item_id] = self._items.get(item_id,0)+qty
    def remove(self, item_id: str, qty: int=1):
        if self._items.get(item_id,0)<qty: raise ValueError("Not enough items")
        self._items[item_id]-=qty
        if self._items[item_id]<=0: del self._items[item_id]
    def has(self, item_id: str, qty: int=1) -> bool:
        return self._items.get(item_id,0)>=qty
    def snapshot(self): return dict(self._items)
EOF

cat > tests/unit/test_event_schema_loading.py <<'EOF'
from platinum.events.loader import load_events
def test_events_load_and_validate():
    reg = load_events()
    assert reg.by_id("story.start") is not None
EOF

echo "Skeleton created."
EOF

chmod +x setup_skeleton.sh
