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
    flags: dict[str, bool] = field(default_factory=dict)
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

class BattleCore:
    def __init__(self, rng: Optional[random.Random] = None, message_cb: Optional[Callable[[str], None]] = None):
        self.rng = rng or random.Random()
        self.message_cb = message_cb

    def _msg(self, text: str):
        if self.message_cb: self.message_cb(text)
        else: print(text)

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

    def apply_damage(self, target: Battler, amount: int):
        if target.current_hp is None:
            target.current_hp = int(target.stats.get("hp", 1))
        target.current_hp = max(0, target.current_hp - amount)
        if target.current_hp <= 0:
            self._msg(f"{target.name} fainted!")

    def end_of_turn(self, battlers: List[Battler], field: FieldState):
        for b in battlers:
            if b.status == "psn":
                dmg = max(1, b.stats["hp"] // 8)
                self.apply_damage(b, dmg)
                self._msg(f"{b.name} is hurt by poison!")
            elif b.status == "brn":
                dmg = max(1, b.stats["hp"] // 8)
                self.apply_damage(b, dmg)
                self._msg(f"{b.name} is hurt by its burn!")
            elif b.status == "tox":
                # Increment toxic stage (cap at 15 like main games); first damaging stage = 1
                b.toxic_stage = (b.toxic_stage + 1) if b.toxic_stage > 0 else 1
                if b.toxic_stage > 15: b.toxic_stage = 15
                dmg = max(1, (b.stats["hp"] * b.toxic_stage) // 16)
                self.apply_damage(b, dmg)
                self._msg(f"{b.name} is badly poisoned!")

            if field.weather == "sand" and not any(t in _DEF_WEATHER_IMMUNITY["sand"] for t in b.types):
                dmg = max(1, b.stats["hp"] // 16)
                self.apply_damage(b, dmg)
                self._msg(f"{b.name} is buffeted by the sandstorm!")
            elif field.weather == "hail" and not any(t in _DEF_WEATHER_IMMUNITY["hail"] for t in b.types):
                dmg = max(1, b.stats["hp"] // 16)
                self.apply_damage(b, dmg)
                self._msg(f"{b.name} is pelted by hail!")

            if (b.current_hp is not None and b.current_hp > 0 and
                (b.item or "").lower() == "leftovers" and b.current_hp < b.stats["hp"]):
                heal = max(1, b.stats["hp"] // 16)
                b.current_hp = min(b.stats["hp"], b.current_hp + heal)
                self._msg(f"{b.name} restored a little HP with Leftovers.")

    def turn_order(self, a: Battler, b: Battler, move_a: Move, move_b: Move) -> List[tuple[Battler, Move]]:
        if move_a.priority != move_b.priority:
            return [(a, move_a), (b, move_b)] if move_a.priority > move_b.priority else [(b, move_b), (a, move_a)]
        speed_a = a.stats["speed"] * stage_multiplier_stat(a.stages.speed)
        speed_b = b.stats["speed"] * stage_multiplier_stat(b.stages.speed)
        if a.status == "par": speed_a *= 0.25
        if b.status == "par": speed_b *= 0.25
        if speed_a != speed_b:
            return [(a, move_a), (b, move_b)] if speed_a > speed_b else [(b, move_b), (a, move_a)]
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
                        self.apply_damage(acting, dmg)
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
            elif mv.flags.get('charge') and acting.charging_move is None:
                # Begin charging: skip damage this turn
                acting.charging_move = mv
                acting.charging_turns_left = 1  # simple two-turn assumption
                self._msg(f"{acting.name} began charging {mv.name}!")
                continue
            if not self.accuracy_check(acting, opp, mv):
                self._msg(f"{acting.name}'s {mv.name} missed!")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            result = self.calc_damage(acting, opp, mv, field)
            if mv.category == "status":
                # Apply simple status/stat changes to opponent or user as heuristic
                applied_any = False
                for sc in mv.stat_changes:
                    try:
                        chance = int(sc.get("chance", 100) or 100)
                    except Exception:
                        chance = 100
                    if self.rng.randint(1,100) <= chance:
                        stat = sc.get("stat")
                        try:
                            change_val = int(sc.get("change", 0) or 0)
                        except Exception:
                            change_val = 0
                        if stat in {"attack","defense","sp-atk","sp-def","speed"} and change_val != 0:
                            attr = stat.replace("-","_")
                            target_entity = acting if change_val > 0 else opp
                            cur = getattr(target_entity.stages, attr if attr != "sp_atk" else "sp_atk")
                            setattr(target_entity.stages, attr if attr != "sp_atk" else "sp_atk", _clamp_stage(cur + change_val))
                            applied_any = True
                if mv.ailment and mv.ailment not in {"none","unknown"} and opp.status == "none":
                    if self.rng.randint(1,100) <= (mv.ailment_chance or 100):
                        status_map = {
                            'paralysis':'par','burn':'brn','poison':'psn','toxic':'tox','sleep':'slp','freeze':'frz'
                        }
                        code = status_map.get(mv.ailment, mv.ailment[:3])
                        self._apply_status(opp, code)
                        applied_any = True
                # Healing / curing support moves
                mv_name = mv.name.lower()
                if mv_name == 'rest':
                    if acting.current_hp == acting.stats['hp'] and acting.status == 'none':
                        self._msg(f"{acting.name} used Rest... but it failed!")
                    else:
                        acting.current_hp = acting.stats['hp']
                        # Clear status then apply sleep (overwrite existing status even if none)
                        self._cure_status(acting, announce=False)
                        self._apply_status(acting, 'slp')
                        self._msg(f"{acting.name} fell asleep and regained health!")
                        applied_any = True
                elif mv_name == 'refresh':
                    if acting.status in {'brn','par','psn','tox'}:
                        self._cure_status(acting)
                        applied_any = True
                elif mv_name in {'heal bell','aromatherapy'}:
                    # Simplified: heals only user in this 1v1 context
                    if acting.status != 'none':
                        self._cure_status(acting)
                        applied_any = True
                if applied_any:
                    self._msg(f"{acting.name} used {mv.name}! Effects applied.")
                else:
                    self._msg(f"{acting.name} used {mv.name}! But nothing happened.")
                if mv.max_pp > 0 and mv.pp > 0:
                    mv.pp -= 1
                continue
            if result["effectiveness"] == 0:
                self._msg("It doesn't affect the target...")
            total_damage = 0
            for idx, h in enumerate(result["hits"], 1):
                if h["damage"] <= 0: continue
                self.apply_damage(opp, h["damage"])
                total_damage += h["damage"]
                multi_prefix = f" (hit {idx})" if len(result['hits']) > 1 else ""
                crit_txt = " A critical hit!" if h["crit"] else ""
                eff_mult = result["effectiveness"]
                eff_txt = "" if eff_mult == 1 else (" It's super effective!" if eff_mult > 1 else " It's not very effective...")
                self._msg(f"{acting.name} used {mv.name}!{multi_prefix}{crit_txt}{eff_txt}")
                if opp.current_hp is not None and opp.current_hp <= 0:
                    break
            # Drain / recoil
            if total_damage > 0 and mv.drain_ratio:
                num, den = mv.drain_ratio
                heal = max(1, (total_damage * num)//den)
                if acting.current_hp is not None:
                    acting.current_hp = min(acting.stats["hp"], acting.current_hp + heal)
                    self._msg(f"{acting.name} restored HP!")
            if total_damage > 0 and mv.recoil_ratio:
                rn, rd = mv.recoil_ratio
                recoil = max(1, (total_damage * rn)//rd)
                self.apply_damage(acting, recoil)
                self._msg(f"{acting.name} is damaged by recoil!")
            # Ailment chance for damaging moves
            if total_damage > 0 and mv.ailment and mv.ailment not in {"none","unknown"} and opp.status == "none":
                if self.rng.randint(1,100) <= (mv.ailment_chance or 0):
                    status_map = {
                        'paralysis':'par','burn':'brn','poison':'psn','toxic':'tox','sleep':'slp','freeze':'frz'
                    }
                    code = status_map.get(mv.ailment, mv.ailment[:3])
                    if code not in {'slp','frz'} or opp.status == 'none':
                        self._apply_status(opp, code)
            # Flinch chance
            if total_damage > 0 and mv.flinch_chance and opp.current_hp and opp.current_hp > 0:
                if self.rng.randint(1,100) <= mv.flinch_chance:
                    opp.flinched = True
            # Contact ability reactive effects
            self._contact_reactive(acting, opp, mv, total_damage)
            # Clear charging state after execution
            if acting.charging_move is mv and acting.charging_turns_left == 0:
                acting.charging_move = None
            if mv.max_pp > 0 and mv.pp > 0:
                mv.pp -= 1
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
        ability = (defender.ability or '').lower()
        if ability == 'rough-skin':
            thorn = max(1, defender.stats['hp']//16)
            self.apply_damage(attacker, thorn)
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
    def _apply_status(self, target: Battler, code: str):
        if target.status != 'none':
            return
        target.status = code
        if code == 'slp':
            # Sleep lasts 1-7 turns in Gen IV after the turn it is set; we model 2-5 for simplicity
            target.sleep_turns = self.rng.randint(2,5)
        elif code == 'tox':
            target.toxic_stage = 0  # will increment at end of turn
        self._msg(f"{target.name} is afflicted with {code}!")

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
