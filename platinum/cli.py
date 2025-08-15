from __future__ import annotations
from platinum.system.settings import Settings
from platinum.system.save import GameState, save_game, load_latest
from platinum.core.logging import logger
from platinum.dialogue.manager import DialogueManager
from platinum.events.loader import load_events
from platinum.events.engine import EventEngine
from platinum.battle.service import battle_service
from platinum.ui.menu import main_menu, options_submenu
from platinum.ui.opening import show_opening_sequence
from platinum.overworld import run_overworld

class GameContext:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.flags: set[str] = set()
        self.dialogue = DialogueManager(settings)
        self.events = EventEngine(self)
        self.battle_service = battle_service
        # Primary game state
        self.state = GameState()
        self._session_start_ts: float | None = None
        self._autosave_suspended: bool = False
        # Early backrefs for dialogue placeholder substitution
        try:
            settings._game_context = self  # type: ignore[attr-defined]
            self.dialogue._game_context = self  # type: ignore[attr-defined]
        except Exception:
            pass

    def set_flag(self, flag: str):
        if flag not in self.flags:
            self.flags.add(flag)
            self.events.on_flag_set(flag)
            self.state.flags = sorted(self.flags)
            if self.settings.data.autosave:
                self._autosave()

    def clear_flag(self, flag: str):
        if flag in self.flags:
            self.flags.remove(flag)
            self.state.flags = sorted(self.flags)
            if self.settings.data.autosave:
                self._autosave()

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def debug_flags(self):
        return sorted(self.flags)

    # --- State helpers ---
    def begin_session(self):
        import time
        self._session_start_ts = time.time()

    def _accumulate_play_time(self):
        import time
        if self._session_start_ts is not None:
            delta = time.time() - self._session_start_ts
            self.state.play_time_seconds += int(delta)
            self._session_start_ts = time.time()

    def _autosave(self):
        if self._autosave_suspended:
            return
        self._accumulate_play_time()
        save_game(self.state)

    def add_money(self, amount: int):
        self.state.money = max(0, self.state.money + amount)
        if self.settings.data.autosave:
            self._autosave()

    def add_item(self, item: str, qty: int = 1):
        inv = self.state.inventory
        inv[item] = inv.get(item, 0) + qty
        if self.settings.data.autosave:
            self._autosave()

    def set_location(self, location: str):
        self.state.location = location
        if self.settings.data.autosave:
            self._autosave()

    # --- Party management (enforce 1..6) ---
    def add_party_member(self, member):
        """Add a PartyMember respecting party size limit (max 6).

        If party already has 6, append to pc_box instead.
        """
        party = self.state.party
        if len(party) < 6:
            party.append(member)
            target = 'party'
        else:
            self.state.pc_box.append(member)
            target = 'pc_box'
        if self.settings.data.autosave:
            self._autosave()
        return target

    def party_is_full(self) -> bool:
        return len(self.state.party) >= 6

    def remove_party_member(self, index: int) -> bool:
        """Remove member at index if more than one remains.

        Returns True if removed, False if rejected (would drop below one or invalid index).
        """
        if index < 0 or index >= len(self.state.party):
            return False
        if len(self.state.party) <= 1:
            return False
        self.state.party.pop(index)
        if self.settings.data.autosave:
            self._autosave()
        return True

    # --- Autosave suspension (batch operations) ---
    def suspend_autosave(self):
        self._autosave_suspended = True

    def resume_autosave(self, flush: bool = True):
        was = self._autosave_suspended
        self._autosave_suspended = False
        if flush and was and self.settings.data.autosave:
            self._autosave()

def start_new_game(ctx: GameContext):
    print("\n== New Game ==\n")
    # Fresh state & session start
    ctx.state = GameState()
    ctx.begin_session()
    events = load_events()
    ctx.events.register_batch(events)
    
    # First ensure spawn location is set
    ctx.set_location("twinleaf_town_bedroom")
    
    # Then trigger Rowan monologue (game_start trigger) BEFORE any player identity input
    ctx.suspend_autosave()
    try:
        ctx.events.dispatch_trigger({"type": "game_start"})
    finally:
        ctx.resume_autosave(flush=True)
    # 2. Player self-identification (name + gender) then rival name
    default_player = "PLAYER"
    default_rival = "RIVAL"
    gender_map = {"m": "male", "f": "female", "o": "other"}
    try:
        pn = input(f"Enter your name [{default_player}]: ").strip()
    except EOFError:
        pn = ''
    try:
        gn_raw = input("Select gender (M/F/O) [Unspecified]: ").strip().lower()
    except EOFError:
        gn_raw = ''
    try:
        rn = input(f"Enter your rival's name [{default_rival}]: ").strip()
    except EOFError:
        rn = ''
    ctx.state.player_name = pn or default_player
    ctx.state.player_gender = gender_map.get(gn_raw[:1], "unspecified")
    # Assistant counterpart: Dawn if player chooses boy (male) else Lucas if girl (female). Default Dawn otherwise.
    ctx.state.assistant = 'lucas' if ctx.state.player_gender == 'female' else 'dawn'
    ctx.state.rival_name = rn or default_rival
    
    # Now that player identity is set, trigger story progression
    ctx.set_flag("story_started")
    
    # 3. Mom & rival plan are now player-driven: talk to Mom downstairs to set rival_introduced; leaving house afterward triggers lake plan.
    if not ctx.has_flag("starter_chosen"):
        print("(Head downstairs, talk to Mom, then exit north toward Lake Verity.)")
    # 4. Enter overworld; subsequent triggers (lake shore & tall grass intercept) will initiate starter sequence
    run_overworld(ctx)

def continue_game(ctx: GameContext):
    gs = load_latest()
    if not gs:
        print("No save to load.")
        input("Press Enter...")
        return
    ctx.state = gs
    ctx.flags = set(gs.flags)
    ctx.begin_session()
    print(f"Loaded save for {gs.player_name} at {gs.location} (Badges: {len(gs.badges)})")
    input("Press Enter to continue...")

def manual_save(ctx: GameContext):
    # Offer save slot selection / overwrite
    from platinum.system.save import list_saves, save_game_slot
    saves = list_saves()
    print("\n-- Save Game --")
    for i, path in enumerate(saves, 1):
        print(f"{i}) {path.name}")
    print("N) New Slot")
    choice = input("Select slot or N: ").strip().lower()
    if choice == "n" or choice == "":
        ctx._autosave()
        print("Saved to new slot.")
    elif choice.isdigit():
        idx = int(choice)
        ctx._accumulate_play_time()
        save_game_slot(ctx.state, idx)
        print(f"Overwrote slot {idx:02d}.")
    else:
        print("Cancelled.")
    input("Press Enter to continue...")

def run():
    settings = Settings.load()
    # Defensive fallback if old settings file lacked log_level
    log_level = getattr(settings.data, "log_level", "INFO")
    from platinum.core.logging import logger as global_logger
    # If debug flag is off, quiet down INFO spam by raising threshold to WARN (raw playthrough mode)
    if not getattr(settings.data, 'debug', False) and log_level in {"INFO","DEBUG"}:
        global_logger.set_level("WARN")
    elif log_level in {"DEBUG","INFO","WARN","ERROR"}:
        global_logger.set_level(log_level)  # type: ignore[arg-type]
    ctx = GameContext(settings)
    # Back-reference for dialogue placeholder substitution
    settings._game_context = ctx  # type: ignore[attr-defined]
    ctx.dialogue._game_context = ctx  # type: ignore[attr-defined]
    # Auto-run opening sequence (no need for user to press Enter to start typing)
    show_opening_sequence()
    while True:
        choice = main_menu()
        if choice == "new":
            start_new_game(ctx)
        elif choice == "continue":
            continue_game(ctx)
        elif choice == "overworld":
            if ctx.state.party:
                run_overworld(ctx)
            else:
                print("Start or continue a game first to enter the overworld.")
                input("Press Enter...")
        elif choice == "save":
            manual_save(ctx)
        elif choice == "options":
            options_submenu(settings)
        elif choice == "flags":
            print("Flags:", ", ".join(ctx.debug_flags()) or "(none)")
            input("Press Enter to continue...")
        elif choice == "quit":
            print("Goodbye!")
            break
    settings.save()

if __name__ == "__main__":
    run()