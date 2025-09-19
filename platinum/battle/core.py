"""Improved (still partial) Gen IV style battle core.

See patch description in previous attempt; this is the standalone creation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, Callable, List
import random
from .obedience import level_cap_for_badges, disobedience_chance

_TYPE_CHART: Dict[str, Dict[str, float]] = {
    # Gen IV accurate (no Fairy type)
    "normal":  {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":    {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":   {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "grass":   {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "electric":{"water": 2.0,"electric": 0.5,"grass": 0.5,"ground": 0.0,"flying": 2.0,"dragon": 0.5},
    "ice":     {"fire": 0.5,"water": 0.5,"grass": 2.0,"ground": 2.0,"flying": 2.0,"dragon": 2.0,"steel": 0.5},
    "fighting":{"normal": 2.0,"ice": 2.0,"rock": 2.0,"dark": 2.0,"steel": 2.0,"poison": 0.5,"flying": 0.5,"psychic": 0.5,"bug": 0.5,"ghost": 0.0},
    "poison":  {"grass": 2.0,"poison": 0.5,"ground": 0.5,"rock": 0.5,"ghost": 0.5,"steel": 0.0},
    "ground":  {"fire": 2.0,"electric": 2.0,"poison": 2.0,"rock": 2.0,"steel": 2.0,"grass": 0.5,"bug": 0.5,"flying": 0.0},
    "flying":  {"grass": 2.0,"fighting": 2.0,"bug": 2.0,"electric": 0.5,"rock": 0.5,"steel": 0.5},
    "psychic": {"fighting": 2.0,"poison": 2.0,"psychic": 0.5,"steel": 0.5,"dark": 0.0},
    "bug":     {"grass": 2.0,"psychic": 2.0,"dark": 2.0,"fire": 0.5,"fighting": 0.5,"poison": 0.5,"flying": 0.5,"ghost": 0.5,"steel": 0.5},
    "rock":    {"fire": 2.0,"ice": 2.0,"flying": 2.0,"bug": 2.0,"fighting": 0.5,"ground": 0.5,"steel": 0.5},
    "ghost":   {"ghost": 2.0,"psychic": 2.0,"dark": 0.5,"normal": 0.0},
    "dragon":  {"dragon": 2.0,"steel": 0.5},
    "dark":    {"ghost": 2.0,"psychic": 2.0,"fighting": 0.5,"dark": 0.5},
    "steel":   {"ice": 2.0,"rock": 2.0,"fire": 0.5,"water": 0.5,"electric": 0.5,"steel": 0.5},
}

_DEF_WEATHER_IMMUNITY = {
    "sand": {"rock", "ground", "steel"},
    "hail": {"ice"}
}

_CRIT_TABLE = {0: 1/16, 1: 1/8, 2: 1/4, 3: 1/3, 4: 1/2}

# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def _clamp_stage(stage: int) -> int: return max(-6, min(6, int(stage)))

def stage_multiplier_stat(stage: int) -> float:
    s = _clamp_stage(stage)
    return (2 + s)/2 if s >= 0 else 2/(2 - s)

def stage_multiplier_acc_eva(stage: int) -> float:
    s = _clamp_stage(stage)
    return (3 + s)/3 if s >= 0 else 3/(3 - s)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Stages:
    attack: int = 0
    defense: int = 0
    sp_atk: int = 0
    sp_def: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0

@dataclass
class Move:
    name: str
    type: str
    category: str  # physical | special | status
    power: int = 0
    accuracy: Optional[int] = 100
    priority: int = 0
    crit_rate_stage: int = 0
    hits: Optional[Tuple[int, int]] = None
    drain_ratio: Optional[Tuple[int, int]] = None
    recoil_ratio: Optional[Tuple[int, int]] = None
    high_crit: bool = False
    flinch_chance: int = 0
    ailment: Optional[str] = None
    ailment_chance: int = 0
    stat_changes: list[dict[str, int | str]] = field(default_factory=list)  # {'stat','change','chance'}
    target: str = "selected-pokemon"
    # Flags may contain booleans (contact, sound, etc.) and internal metadata strings (e.g., 'internal' move slug)
    flags: dict[str, Any] = field(default_factory=dict)
    multi_turn: Optional[Tuple[int,int]] = None  # charge turns (min,max) if any
    max_pp: int = 0
    pp: int = 0  # current PP; 0 => cannot select (Struggle not yet implemented fully)

@dataclass
class Battler:
    species_id: int
    name: str
    level: int
    types: Tuple[str, ...]
    stats: Dict[str, int]
    moves: List[Move] = field(default_factory=list)
    stages: Stages = field(default_factory=Stages)
    status: str = "none"
    ability: Optional[str] = None
    item: Optional[str] = None
    current_hp: Optional[int] = None  # lazily initialized to max HP
    sleep_turns: int = 0
    toxic_stage: int = 0
    confusion_turns: int = 0
    flinched: bool = False
    charging_move: Optional[Move] = None
    charging_turns_left: int = 0
    # True if the battler is semi-invulnerable this turn (e.g., Fly/Dig/Bounce/Dive charge turn)
    semi_invulnerable: bool = False
    # True if the battler must recharge this turn (Hyper Beam-style)
    must_recharge: bool = False
    # Passive HP recovery each turn from Aqua Ring
    aqua_ring: bool = False
    # If True, the battler's ability is suppressed (e.g., by Gastro Acid)
    ability_suppressed: bool = False

    def __post_init__(self):
        # Always normalize current_hp to an int to simplify downstream logic
        max_hp = int(self.stats.get("hp", 1))
        if self.current_hp is None or self.current_hp <= 0 or self.current_hp > max_hp:
            self.current_hp = max_hp
        # Trim move list to at most 4 like canonical games
        if len(self.moves) > 4:
            self.moves = self.moves[-4:]

@dataclass
class FieldState:
    weather: Optional[str] = None
    reflect: bool = False
    light_screen: bool = False
    turn: int = 0
    # Durations (in turns) for field effects
    weather_turns: int = 0
    reflect_turns: int = 0
    light_screen_turns: int = 0
    # Additional field effects
    trick_room_turns: int = 0
    mist_turns: int = 0
    stealth_rock: bool = False

class BattleCore:
    def __init__(self, rng: Optional[random.Random] = None, message_cb: Optional[Callable[[str], None]] = None):
        self.rng = rng or random.Random()
        self.message_cb = message_cb
        # Optional callback for UI to observe HP changes
        self.hp_change_cb: Optional[Callable[[Battler, int, int, dict], None]] = None

    def _msg(self, text: str):
        if self.message_cb: self.message_cb(text)
        else: print(text)

    def _notify_hp_change(self, target: 'Battler', old_hp: int, new_hp: int, meta: dict):
        cb = getattr(self, 'hp_change_cb', None)
        if cb:
            try:
                cb(target, int(old_hp), int(new_hp), dict(meta))
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Mechanics
    # ------------------------------------------------------------------
    def get_effectiveness(self, move_type: str, target_types: Tuple[str, ...]) -> float:
        mult = 1.0
        offense = _TYPE_CHART.get(move_type.lower(), {})
        for t in target_types:
            mult *= offense.get(t.lower(), 1.0)
        return mult

    def roll_crit(self, crit_stage: int) -> bool:
        p = _CRIT_TABLE.get(max(0, min(int(crit_stage), 4)), 1/16)
        return self.rng.random() < p

    def accuracy_check(self, user: Battler, target: Battler, move: Move) -> bool:
        # Attacks generally miss when the target is semi-invulnerable unless the move is flagged to hit them
        try:
            if getattr(target, 'semi_invulnerable', False):
                if not bool(move.flags.get('hits_semi_invulnerable', False)):
                    return False
        except Exception:
            pass
        if move.accuracy is None: return True
        acc_mod = stage_multiplier_acc_eva(user.stages.accuracy)
        eva_mod = stage_multiplier_acc_eva(target.stages.evasion)
        chance = move.accuracy * (acc_mod / eva_mod)
        return self.rng.random() * 100 < chance

    def calc_damage(self, user: Battler, target: Battler, move: Move, field: FieldState) -> Dict[str, Any]:
        if move.category == "status" or move.power <= 0:
            return {"hits": [], "total": 0, "crit_any": False, "effectiveness": 1.0}
        atk_stat = "atk" if move.category == "physical" else "sp_atk"
        def_stat = "def" if move.category == "physical" else "sp_def"
        stage_name_map = {"atk": "attack", "def": "defense", "sp_atk": "sp_atk", "sp_def": "sp_def"}

        hit_count = 1
        if move.hits:
            lo, hi = move.hits
            hit_count = self.rng.randint(lo, hi)

        hit_results: list[dict[str, Any]] = []
        effectiveness: Optional[float] = None
        crit_any = False

        for _ in range(hit_count):
            atk_stage_val = getattr(user.stages, stage_name_map[atk_stat])
            def_stage_val = getattr(target.stages, stage_name_map[def_stat])
            atk_mod = stage_multiplier_stat(atk_stage_val)
            def_mod = stage_multiplier_stat(def_stage_val)

            atk_val = user.stats[atk_stat] * atk_mod
            def_val = target.stats[def_stat] * def_mod

            if move.category == "physical" and user.status == "brn" and (user.ability or "").lower() != "guts":
                atk_val *= 0.5

            base = (((2 * user.level / 5) + 2) * move.power * atk_val / max(1, def_val)) / 50 + 2

            if field.weather == "sun":
                if move.type == "fire": base *= 1.5
                elif move.type == "water": base *= 0.5
            elif field.weather == "rain":
                if move.type == "water": base *= 1.5
                elif move.type == "fire": base *= 0.5

            crit_stage = move.crit_rate_stage + (1 if move.high_crit else 0)
            crit = self.roll_crit(crit_stage)
            if crit:
                crit_any = True
                eff_atk_stage = max(0, atk_stage_val)
                eff_def_stage = min(0, def_stage_val)
                atk_val_c = user.stats[atk_stat] * stage_multiplier_stat(eff_atk_stage)
                def_val_c = target.stats[def_stat] * stage_multiplier_stat(eff_def_stage)
                base = (((2 * user.level / 5) + 2) * move.power * atk_val_c / max(1, def_val_c)) / 50 + 2
                base *= 2
            else:
                if move.category == "physical" and field.reflect:
                    base *= 0.5
                elif move.category == "special" and field.light_screen:
                    base *= 0.5

            base *= self.rng.uniform(0.85, 1.0)

            if move.type in user.types:
                if (user.ability or "").lower() == "adaptability": base *= 2.0
                else: base *= 1.5

            eff = self.get_effectiveness(move.type, target.types)
            if effectiveness is None: effectiveness = eff
            base *= eff

            dmg = int(max(1, base)) if eff > 0 else 0
            hit_results.append({"damage": dmg, "crit": crit})
            if eff == 0:
                break

        total = sum(h["damage"] for h in hit_results)
        return {"hits": hit_results, "total": total, "crit_any": crit_any, "effectiveness": effectiveness or 1.0}

    def apply_damage(self, target: Battler, amount: int, *, cause: str = 'damage', meta: Optional[dict] = None):
        if target.current_hp is None:
            target.current_hp = int(target.stats.get("hp", 1))
        old = int(target.current_hp)
        target.current_hp = max(0, old - int(amount))
        self._notify_hp_change(target, old, target.current_hp, {"cause": cause, **(meta or {})})
        if target.current_hp <= 0:
            self._msg(f"{target.name} fainted!")

    def apply_heal(self, target: Battler, amount: int, *, cause: str = 'other', meta: Optional[dict] = None):
        if target.current_hp is None:
            target.current_hp = int(target.stats.get("hp", 1))
        old = int(target.current_hp)
        target.current_hp = min(int(target.stats.get("hp", 1)), old + int(amount))
        self._notify_hp_change(target, old, target.current_hp, {"cause": cause, **(meta or {})})

    def end_of_turn(self, battlers: List[Battler], field: FieldState):
        for b in battlers:
            if b.status == "psn":
                dmg = max(1, b.stats["hp"] // 8)
                self.apply_damage(b, dmg, cause='status', meta={'status': 'psn'})
                self._msg(f"{b.name} is hurt by poison!")
            elif b.status == "brn":
                dmg = max(1, b.stats["hp"] // 8)
                self.apply_damage(b, dmg, cause='status', meta={'status': 'brn'})
                self._msg(f"{b.name} is hurt by its burn!")
            elif b.status == "tox":
                # Increment toxic stage (cap at 15 like main games); first damaging stage = 1
                b.toxic_stage = (b.toxic_stage + 1) if b.toxic_stage > 0 else 1
                if b.toxic_stage > 15: b.toxic_stage = 15
                dmg = max(1, (b.stats["hp"] * b.toxic_stage) // 16)
                self.apply_damage(b, dmg, cause='status', meta={'status': 'tox', 'stage': b.toxic_stage})
                self._msg(f"{b.name} is badly poisoned!")

            if field.weather == "sand" and not any(t in _DEF_WEATHER_IMMUNITY["sand"] for t in b.types):
                dmg = max(1, b.stats["hp"] // 16)
                self.apply_damage(b, dmg, cause='weather', meta={'weather': 'sand'})
                self._msg(f"{b.name} is buffeted by the sandstorm!")
            elif field.weather == "hail" and not any(t in _DEF_WEATHER_IMMUNITY["hail"] for t in b.types):
                dmg = max(1, b.stats["hp"] // 16)
                self.apply_damage(b, dmg, cause='weather', meta={'weather': 'hail'})
                self._msg(f"{b.name} is pelted by hail!")

            if (b.current_hp is not None and b.current_hp > 0 and
                (b.item or "").lower() == "leftovers" and b.current_hp < b.stats["hp"]):
                heal = max(1, b.stats["hp"] // 16)
                self.apply_heal(b, heal, cause='item', meta={'item': 'leftovers'})
                self._msg(f"{b.name} restored a little HP with Leftovers.")
            # Aqua Ring passive heal (1/16 max HP)
            if (b.current_hp is not None and b.current_hp > 0 and b.aqua_ring and b.current_hp < b.stats["hp"]):
                heal = max(1, b.stats["hp"] // 16)
                self.apply_heal(b, heal, cause='field', meta={'effect': 'aqua-ring'})
                self._msg(f"{b.name} restored HP with Aqua Ring!")

        # Decrement field effect durations and clear when over
        if field.weather_turns > 0:
            field.weather_turns -= 1
            if field.weather_turns == 0 and field.weather is not None:
                if field.weather == 'sun': self._msg("The sunlight faded.")
                elif field.weather == 'rain': self._msg("The rain stopped.")
                elif field.weather == 'sand': self._msg("The sandstorm subsided.")
                elif field.weather == 'hail': self._msg("The hail stopped.")
                field.weather = None
        if field.reflect_turns > 0:
            field.reflect_turns -= 1
            if field.reflect_turns == 0 and field.reflect:
                field.reflect = False
                self._msg("Reflect wore off!")
        if field.light_screen_turns > 0:
            field.light_screen_turns -= 1
            if field.light_screen_turns == 0 and field.light_screen:
                field.light_screen = False
                self._msg("Light Screen wore off!")
        if field.trick_room_turns > 0:
            field.trick_room_turns -= 1
            # Mark battlers for next turn's turn order inversion
            active = field.trick_room_turns > 0
            for b in battlers:
                setattr(b, '_trick_room_active', active)
            if not active:
                self._msg("The twisted dimensions returned to normal!")
        if field.mist_turns > 0:
            field.mist_turns -= 1
            if field.mist_turns == 0:
                self._msg("The mist faded!")

    def turn_order(self, a: Battler, b: Battler, move_a: Move, move_b: Move) -> List[tuple[Battler, Move]]:
        if move_a.priority != move_b.priority:
            return [(a, move_a), (b, move_b)] if move_a.priority > move_b.priority else [(b, move_b), (a, move_a)]
        speed_a = a.stats["speed"] * stage_multiplier_stat(a.stages.speed)
        speed_b = b.stats["speed"] * stage_multiplier_stat(b.stages.speed)
        if a.status == "par": speed_a *= 0.25
        if b.status == "par": speed_b *= 0.25
        trick = bool(getattr(a, '_trick_room_active', False) or getattr(b, '_trick_room_active', False))
        if speed_a != speed_b:
            if (speed_a > speed_b) ^ trick:
                return [(a, move_a), (b, move_b)]
            else:
                return [(b, move_b), (a, move_a)]
        return [(a, move_a), (b, move_b)] if self.rng.random() < 0.5 else [(b, move_b), (a, move_a)]

    def single_turn(self, user: Battler, user_move: Move, target: Battler, target_move: Optional[Move], field: FieldState):
        order = self.turn_order(user, target, user_move, target_move or user_move)
        for acting, mv in order:
            opp = target if acting is user else user
            if acting.current_hp is None:
                acting.current_hp = int(acting.stats.get("hp", 1))
            if acting.current_hp <= 0:
                continue
            try:
                badge_count = int(getattr(acting, 'badge_count', 8))
            except Exception:
                badge_count = 8
            cap = level_cap_for_badges(badge_count)
            if acting.level > cap:
                chance = disobedience_chance(acting.level, cap)
                if self.rng.random() < chance:
                    # Behavior variants
                    roll = self.rng.randint(1, 100)
                    if roll <= 40:
                        self._msg(f"{acting.name} ignored orders!")
                    elif roll <= 70 and acting.current_hp < acting.stats['hp']:
                        # loaf (heal small amount)
                        heal = max(1, acting.stats['hp']//20)
                        acting.current_hp = min(acting.stats['hp'], acting.current_hp + heal)
                        self._msg(f"{acting.name} loafed around and recovered a little HP!")
                    elif roll <= 85:
                        self._msg(f"{acting.name} is loafing around!")
                    else:
                        # hurt itself in confusion style (1/8 max HP)
                        dmg = max(1, acting.stats['hp']//8)
                        self.apply_damage(acting, dmg, cause='self', meta={'reason': 'disobedience'})
                        self._msg(f"{acting.name} was hurt in its disobedience!")
                    continue
            # PP check
            if mv.pp is not None and mv.max_pp > 0 and mv.pp <= 0:
                # Skip move (could implement Struggle); for now treat as fail
                self._msg(f"{acting.name} has no PP left for {mv.name}!")
                continue
            # Flinch check
            if acting.flinched:
                self._msg(f"{acting.name} flinched and couldn't move!")
                acting.flinched = False
                continue
            # Recharge turn takes precedence over other action checks
            if getattr(acting, 'must_recharge', False):
                self._msg(f"{acting.name} must recharge!")
                acting.must_recharge = False
                continue
            # Sleep handling
            if acting.status == 'slp':
                if acting.sleep_turns > 0:
                    acting.sleep_turns -= 1
                if acting.sleep_turns > 0:
                    self._msg(f"{acting.name} is fast asleep.")
                    continue
                else:
                    acting.status = 'none'
                    self._msg(f"{acting.name} woke up!")
            # Freeze handling (20% thaw each turn)
            if acting.status == 'frz':
                if self.rng.randint(1,100) <= 20:
                    acting.status = 'none'
                    self._msg(f"{acting.name} thawed out!")
                else:
                    self._msg(f"{acting.name} is frozen solid!")
                    continue
            # Paralysis action prevention (25%)
            if acting.status == 'par':
                if self.rng.randint(1,100) <= 25:
                    self._msg(f"{acting.name} is fully paralyzed! It can't move!")
                    continue
            # Charging logic (two-turn moves with charge flag: Solar Beam, Sky Attack, etc.)
            if acting.charging_move and acting.charging_move is mv and acting.charging_turns_left > 0:
                acting.charging_turns_left -= 1
                if acting.charging_turns_left > 0:
                    self._msg(f"{acting.name} continues charging {mv.name}!")
                    continue
                else:
                    self._msg(f"{acting.name} unleashes {mv.name}!")
                    # Clear semi-invulnerable on the attack turn
                    acting.semi_invulnerable = False
            elif mv.flags.get('charge') and acting.charging_move is None:
                # Begin charging: skip damage this turn
                acting.charging_move = mv
                acting.charging_turns_left = 1  # simple two-turn assumption
                self._msg(f"{acting.name} began charging {mv.name}!")
                # Some moves make the user semi-invulnerable on the charge turn (e.g., Fly/Dig/Bounce/Dive)
                if bool(mv.flags.get('semi_invulnerable', False)):
                    acting.semi_invulnerable = True
                continue
            if not self.accuracy_check(acting, opp, mv):
                self._msg(f"{acting.name}'s {mv.name} missed!")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            # Special fixed-damage and percent-HP moves handled explicitly
            try:
                internal = (mv.flags or {}).get('internal') if isinstance(mv.flags, dict) else None
                mv_slug = str(internal or mv.name).lower().replace(' ', '-').replace("'", "")
            except Exception:
                mv_slug = str(mv.name).lower()
            special_damage: Optional[int] = None
            if mv_slug == 'dragon-rage':
                special_damage = 40
            elif mv_slug == 'sonic-boom':
                special_damage = 20
            elif mv_slug in {'night-shade','seismic-toss'}:
                special_damage = int(getattr(acting, 'level', 1) or 1)
            elif mv_slug == 'super-fang':
                cur = int(opp.current_hp or opp.stats.get('hp', 1))
                special_damage = max(1, cur // 2)
            elif mv_slug == 'endeavor':
                cur_o = int(opp.current_hp or opp.stats.get('hp', 1))
                cur_u = int(acting.current_hp or acting.stats.get('hp', 1))
                if cur_o > cur_u:
                    special_damage = cur_o - cur_u
                else:
                    special_damage = 0
            elif mv_slug == 'psywave':
                # Simplified fixed damage
                special_damage = max(1, int((getattr(acting, 'level', 1) or 1) * 0.8))
            elif mv_slug == 'present':
                special_damage = 40
            if special_damage is not None:
                # Type immunity check still applies
                try:
                    eff_chk = self.get_effectiveness(mv.type, opp.types)
                except Exception:
                    eff_chk = 1.0
                if eff_chk == 0.0 or special_damage <= 0:
                    self._msg("It doesn't affect the target...")
                else:
                    self.apply_damage(opp, special_damage, cause='move', meta={'move': mv.name, 'fixed': True})
                    self._msg(f"{acting.name} used {mv.name}!")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            # Reactive or item/team dependent moves that won't work in smoke context
            if mv_slug in {'counter','mirror-coat','metal-burst','bide','spit-up','natural-gift','fling','beat-up'}:
                self._msg("But it failed!")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            # Temporary fallback base power for complex formula moves when data power is 0/None
            orig_power = mv.power
            power_overridden = False
            if (orig_power or 0) <= 0:
                fallback_map = {
                    'grass-knot': 60,
                    'low-kick': 60,
                    'gyro-ball': 60,
                    'crush-grip': 60,
                    'wring-out': 60,
                    'punishment': 60,
                    'magnitude': 70,
                    'return': 70,
                    'frustration': 70,
                    'trump-card': 40,
                    'flail': 20,
                    'reversal': 20,
                }
                fb = fallback_map.get(mv_slug)
                if fb is not None:
                    mv.power = fb
                    power_overridden = True
            result = self.calc_damage(acting, opp, mv, field)
            if mv.category == "status":
                # Announce the move first (UI overlay will handle wipe + SFX)
                self._msg(f"{acting.name} used {mv.name}!")
                # If the move's type has no effect on the target (e.g., Electric vs Ground), it fails
                try:
                    eff_chk = self.get_effectiveness(mv.type, opp.types)
                except Exception:
                    eff_chk = 1.0
                if eff_chk == 0.0:
                    self._msg("It doesn't affect the target...")
                    if mv.max_pp > 0 and mv.pp > 0:
                        mv.pp -= 1
                    continue
                # Apply simple status/stat changes to opponent or user.
                applied_any = False
                # Fallbacks for common Gen IV status moves when stat_changes absent in data
                fallback_changes: list[dict[str, int | str]] = []
                try:
                    internal = mv.flags.get('internal') if isinstance(mv.flags, dict) else None
                    if isinstance(internal, str) and internal:
                        base = internal
                    else:
                        base = mv.name
                    mv_slug = str(base).lower().replace(' ', '-').replace("'", "")
                except Exception:
                    mv_slug = str(mv.name).lower()
                if (not mv.stat_changes):
                    # Simple debuffs
                    if mv_slug in {'growl'}:
                        fallback_changes = [{"stat": "attack", "change": -1, "chance": 100}]
                    elif mv_slug in {'leer','tail-whip'}:
                        fallback_changes = [{"stat": "defense", "change": -1, "chance": 100}]
                    elif mv_slug in {'string-shot'}:
                        fallback_changes = [{"stat": "speed", "change": -1, "chance": 100}]
                    elif mv_slug in {'cotton-spore'}:
                        fallback_changes = [{"stat": "speed", "change": -2, "chance": 100}]
                    # Simple self-buffs
                    elif mv_slug in {'acid-armor','iron-defense'}:
                        fallback_changes = [{"stat": "defense", "change": +2, "chance": 100}]
                    elif mv_slug in {'agility','rock-polish'}:
                        fallback_changes = [{"stat": "speed", "change": +2, "chance": 100}]
                    elif mv_slug in {'amnesia'}:
                        fallback_changes = [{"stat": "sp-def", "change": +2, "chance": 100}]
                    elif mv_slug in {'barrier','withdraw','harden'}:
                        fallback_changes = [{"stat": "defense", "change": +1, "chance": 100}]
                    elif mv_slug in {'howl','meditate','sharpen'}:
                        fallback_changes = [{"stat": "attack", "change": +1, "chance": 100}]
                    elif mv_slug in {'swords-dance'}:
                        fallback_changes = [{"stat": "attack", "change": +2, "chance": 100}]
                    elif mv_slug in {'nasty-plot'}:
                        fallback_changes = [{"stat": "sp-atk", "change": +2, "chance": 100}]
                    elif mv_slug in {'calm-mind'}:
                        fallback_changes = [{"stat": "sp-atk", "change": +1, "chance": 100}, {"stat": "sp-def", "change": +1, "chance": 100}]
                    elif mv_slug in {'bulk-up'}:
                        fallback_changes = [{"stat": "attack", "change": +1, "chance": 100}, {"stat": "defense", "change": +1, "chance": 100}]
                    elif mv_slug in {'cosmic-power'}:
                        fallback_changes = [{"stat": "defense", "change": +1, "chance": 100}, {"stat": "sp-def", "change": +1, "chance": 100}]
                    elif mv_slug in {'charge'}:
                        fallback_changes = [{"stat": "sp-def", "change": +1, "chance": 100}]
                changes = mv.stat_changes or fallback_changes
                # Helper for stat normalization & nice message text
                def _normalize_stat(s: str) -> str:
                    s = s.replace("_","-").lower()
                    if s in ("special-attack","sp-atk","spatk"): return "sp-atk"
                    if s in ("special-defense","sp-def","spdef"): return "sp-def"
                    return s
                def _stat_label(s: str) -> str:
                    m = {
                        'attack': 'Attack', 'defense': 'Defense', 'sp-atk': 'Special Attack', 'sp-def': 'Special Defense', 'speed': 'Speed', 'accuracy': 'Accuracy', 'evasion': 'Evasion'
                    }
                    return m.get(s, s.title())
                for sc in changes:
                    try:
                        chance = int(sc.get("chance", 100) or 100)  # type: ignore[arg-type]
                    except Exception:
                        chance = 100
                    if self.rng.randint(1,100) <= chance:
                        stat = _normalize_stat(str(sc.get("stat")))
                        try:
                            change_val = int(sc.get("change", 0) or 0)  # type: ignore[arg-type]
                        except Exception:
                            change_val = 0
                        if stat in {"attack","defense","sp-atk","sp-def","speed","accuracy","evasion"} and change_val != 0:
                            attr = stat.replace("-","_")
                            target_entity = acting if change_val > 0 else opp
                            cur = getattr(target_entity.stages, attr)
                            setattr(target_entity.stages, attr, _clamp_stage(cur + change_val))
                            # Message with adverbs for ±2/±3
                            adverb = ""
                            if abs(change_val) == 2:
                                adverb = " sharply"
                            elif abs(change_val) >= 3:
                                adverb = " drastically"
                            direction = " rose!" if change_val > 0 else " fell!"
                            self._msg(f"{target_entity.name}'s {_stat_label(stat)}{adverb}{direction}")
                            applied_any = True
                if mv.ailment and mv.ailment not in {"none","unknown"} and opp.status == "none":
                    if self.rng.randint(1,100) <= (mv.ailment_chance or 100):
                        status_map = {
                            'paralysis':'par','burn':'brn','poison':'psn','toxic':'tox','sleep':'slp','freeze':'frz'
                        }
                        code = status_map.get(mv.ailment, mv.ailment[:3])
                        if self._apply_status(opp, code, move_type=mv.type):
                            applied_any = True
                # Healing / curing support moves
                mv_name = mv_slug
                if mv_name == 'rest':
                    if acting.current_hp == acting.stats['hp'] and acting.status == 'none':
                        self._msg(f"But it failed!")
                    else:
                        heal_amt = int(acting.stats['hp'] - (acting.current_hp or 0))
                        if heal_amt > 0:
                            self.apply_heal(acting, heal_amt, cause='move', meta={'move': 'Rest'})
                        # Clear status then apply sleep (overwrite existing status even if none)
                        self._cure_status(acting, announce=False)
                        self._apply_status(acting, 'slp')
                        self._msg(f"{acting.name} fell asleep and regained health!")
                        applied_any = True
                elif mv_name == 'refresh':
                    if acting.status in {'brn','par','psn','tox'}:
                        self._cure_status(acting)
                        applied_any = True
                elif mv_name in {'heal-bell','aromatherapy'}:
                    # Simplified: heals only user in this 1v1 context
                    if acting.status != 'none':
                        self._cure_status(acting)
                        applied_any = True
                elif mv_name == 'aqua-ring':
                    if not acting.aqua_ring:
                        acting.aqua_ring = True
                        self._msg(f"A veil of water surrounds {acting.name}!")
                        applied_any = True
                elif mv_name == 'magnet-rise':
                    # Simplified: grant temporary levitation
                    if not hasattr(acting, 'levitate_turns'):
                        setattr(acting, 'levitate_turns', 0)
                    if getattr(acting, 'levitate_turns', 0) <= 0:
                        setattr(acting, 'levitate_turns', 5)
                        self._msg(f"{acting.name} levitated with electromagnetism!")
                        applied_any = True
                elif mv_name == 'gastro-acid':
                    # Simplified: suppress the target's ability (no duration handling; lasts while active)
                    if getattr(opp, 'ability', None) and not getattr(opp, 'ability_suppressed', False):
                        opp.ability_suppressed = True
                        self._msg(f"{opp.name}'s Ability was suppressed!")
                        applied_any = True
                elif mv_name == 'mist':
                    field.mist_turns = 5
                    self._msg("A mist shrouded the field!")
                    applied_any = True
                elif mv_name == 'haze':
                    # Reset all battlers' stat changes
                    for b in (acting, opp):
                        b.stages = Stages()
                    self._msg("All stat changes were eliminated!")
                    applied_any = True
                elif mv_name == 'trick-room':
                    field.trick_room_turns = 5
                    self._msg("The dimensions were twisted!")
                    applied_any = True
                elif mv_name == 'stealth-rock':
                    if not field.stealth_rock:
                        field.stealth_rock = True
                        self._msg("Pointed stones float in the air around the foe's team!")
                        applied_any = True
                elif mv_name in {'roar','whirlwind','teleport','destiny-bond','grudge'}:
                    # Not fully simulated here; report a failure message to satisfy smoke
                    self._msg("But it failed!")
                elif mv_name == 'sunny-day':
                    field.weather = 'sun'; field.weather_turns = 5
                    self._msg("The sunlight turned harsh!")
                    applied_any = True
                elif mv_name == 'rain-dance':
                    field.weather = 'rain'; field.weather_turns = 5
                    self._msg("It started to rain!")
                    applied_any = True
                elif mv_name == 'sandstorm':
                    field.weather = 'sand'; field.weather_turns = 5
                    self._msg("A sandstorm kicked up!")
                    applied_any = True
                elif mv_name == 'hail':
                    field.weather = 'hail'; field.weather_turns = 5
                    self._msg("It started to hail!")
                    applied_any = True
                elif mv_name == 'reflect':
                    field.reflect = True; field.reflect_turns = 5
                    self._msg("Reflect raised your team's Defense!")
                    applied_any = True
                elif mv_name == 'light-screen':
                    field.light_screen = True; field.light_screen_turns = 5
                    self._msg("Light Screen raised your team's Sp. Def!")
                    applied_any = True
                if not applied_any:
                    self._msg("But nothing happened.")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            if result["effectiveness"] == 0:
                self._msg("It doesn't affect the target...")
            total_damage = 0
            for idx, h in enumerate(result["hits"], 1):
                if h["damage"] <= 0: continue
                eff_mult = result["effectiveness"]
                self.apply_damage(opp, h["damage"], cause='move', meta={'effectiveness': eff_mult, 'move': mv.name, 'attacker': acting.name, 'hit_index': idx, 'multi_hits': len(result['hits'])})
                total_damage += h["damage"]
                multi_prefix = f" (hit {idx})" if len(result['hits']) > 1 else ""
                crit_txt = " A critical hit!" if h["crit"] else ""
                eff_txt = "" if eff_mult == 1 else (" It's super effective!" if eff_mult > 1 else " It's not very effective...")
                self._msg(f"{acting.name} used {mv.name}!{multi_prefix}{crit_txt}{eff_txt}")
                if opp.current_hp is not None and opp.current_hp <= 0:
                    break
            # Drain / recoil
            if total_damage > 0 and mv.drain_ratio:
                num, den = mv.drain_ratio
                heal = max(1, (total_damage * num)//den)
                if heal > 0:
                    self.apply_heal(acting, heal, cause='drain', meta={'move': mv.name})
                    # Use Platinum-accurate text for draining moves
                    if mv.name.lower() in ['absorb', 'mega-drain', 'giga-drain']:
                        self._msg(f"{acting.name} absorbed nutrients from {opp.name}!")
                    elif mv.name.lower() == 'leech-life':
                        self._msg(f"{acting.name} sucked life from {opp.name}!")
                    elif mv.name.lower() == 'dream-eater':
                        self._msg(f"{acting.name} ate {opp.name}'s dream!")
                    elif mv.name.lower() == 'drain-punch':
                        self._msg(f"{acting.name} drained power from {opp.name}!")
                    else:
                        self._msg(f"{acting.name} had its energy drained!")
            if total_damage > 0 and mv.recoil_ratio:
                rn, rd = mv.recoil_ratio
                recoil = max(1, (total_damage * rn)//rd)
                self.apply_damage(acting, recoil, cause='recoil', meta={'move': mv.name})
                self._msg(f"{acting.name} is damaged by recoil!")
            # Ailment chance for damaging moves
            if total_damage > 0 and mv.ailment and mv.ailment not in {"none","unknown"} and opp.status == "none":
                if self.rng.randint(1,100) <= (mv.ailment_chance or 0):
                    status_map = {
                        'paralysis':'par','burn':'brn','poison':'psn','toxic':'tox','sleep':'slp','freeze':'frz'
                    }
                    code = status_map.get(mv.ailment, mv.ailment[:3])
                    if code not in {'slp','frz'} or opp.status == 'none':
                        self._apply_status(opp, code, move_type=mv.type)
            # Flinch chance
            if total_damage > 0 and mv.flinch_chance and opp.current_hp and opp.current_hp > 0:
                if self.rng.randint(1,100) <= mv.flinch_chance:
                    opp.flinched = True
            # Contact ability reactive effects
            self._contact_reactive(acting, opp, mv, total_damage)
            # Clear charging state after execution
            if acting.charging_move is mv and acting.charging_turns_left == 0:
                acting.charging_move = None
            # Set recharge requirement for Hyper Beam-style moves (only after executing the move this turn)
            try:
                internal = (mv.flags or {}).get('internal') if isinstance(mv.flags, dict) else None
                mv_slug = str(internal or mv.name).lower().replace(' ', '-').replace("'", "")
            except Exception:
                mv_slug = str(mv.name).lower()
            if (((mv.flags.get('recharge') if isinstance(mv.flags, dict) else False) or mv_slug in {
                'hyper-beam','giga-impact','roar-of-time','blast-burn','frenzy-plant','hydro-cannon','rock-wrecker'
            }) and not acting.must_recharge):
                acting.must_recharge = True
            if mv.max_pp > 0 and mv.pp > 0:
                mv.pp -= 1
            if power_overridden:
                mv.power = orig_power
        self.end_of_turn([user, target], field)
        # Reset flinch for next turn
        user.flinched = False if user.flinched else user.flinched
        target.flinched = False if target.flinched else target.flinched

    # ------------------------------------------------------------------
    # Reactive effects
    # ------------------------------------------------------------------
    def _contact_reactive(self, attacker: Battler, defender: Battler, move: Move, damage: int):
        # Simple subset of contact-based abilities
        if damage <= 0:
            return
        # Use explicit flag if available, else infer from physical category.
        is_contact = move.flags.get('contact', move.category == 'physical')
        if not is_contact:
            return
        # Ignore suppressed ability
        if getattr(defender, 'ability_suppressed', False):
            ability = ''
        else:
            ability = (defender.ability or '').lower()
        if ability == 'rough-skin':
            thorn = max(1, defender.stats['hp']//16)
            self.apply_damage(attacker, thorn, cause='ability', meta={'ability': 'rough-skin'})
            self._msg(f"{attacker.name} is hurt by Rough Skin!")
        elif ability == 'static' and attacker.status == 'none':
            if self.rng.randint(1,100) <= 30:
                attacker.status = 'par'
                self._msg(f"{attacker.name} is paralyzed by Static!")
        elif ability == 'flame-body' and attacker.status == 'none':
            if self.rng.randint(1,100) <= 30:
                attacker.status = 'brn'
                self._msg(f"{attacker.name} is burned by Flame Body!")
        elif ability == 'poison-point' and attacker.status == 'none':
            if self.rng.randint(1,100) <= 30:
                attacker.status = 'psn'
                self._msg(f"{attacker.name} is poisoned by Poison Point!")

    # ------------------------------------------------------------------
    # Status helper
    # ------------------------------------------------------------------
    def _apply_status(self, target: Battler, code: str, move_type: Optional[str] = None) -> bool:
        if target.status != 'none':
            return False
        # Type-based immunities (Gen IV-friendly subset)
        types = tuple(t.lower() for t in (target.types or ()))
        if code == 'brn' and 'fire' in types:
            return False
        if code in {'psn','tox'} and ('poison' in types or 'steel' in types):
            return False
        if code == 'frz' and 'ice' in types:
            return False
        # If provided a move_type and it has no effect on the target, fail (e.g., Electric vs Ground for Thunder Wave)
        if move_type is not None:
            try:
                if self.get_effectiveness(str(move_type), target.types) == 0.0:
                    return False
            except Exception:
                pass
        target.status = code
        if code == 'slp':
            # Sleep lasts 1-7 turns in Gen IV after the turn it is set; we model 2-5 for simplicity
            target.sleep_turns = self.rng.randint(2,5)
        elif code == 'tox':
            target.toxic_stage = 0  # will increment at end of turn
        self._msg(f"{target.name} is afflicted with {code}!")
        return True

    def _cure_status(self, target: Battler, announce: bool = True):
        if target.status == 'none':
            return
        target.status = 'none'
        target.sleep_turns = 0
        target.toxic_stage = 0
        if announce:
            self._msg(f"{target.name}'s status was cured!")

__all__ = [
    "BattleCore", "Battler", "Move", "Stages", "FieldState",
    "stage_multiplier_stat", "stage_multiplier_acc_eva"
]
