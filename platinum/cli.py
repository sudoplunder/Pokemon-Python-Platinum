from __future__ import annotations
from platinum.system.settings import Settings
from platinum.system.save import GameState, save_game, load_latest, save_temp, delete_temp
from platinum.core.logging import logger
from platinum.dialogue.manager import DialogueManager
from platinum.events.loader import load_events
from platinum.events.engine import EventEngine
from platinum.battle.service import battle_service
from platinum.ui.menu import main_menu, options_submenu
from platinum.ui.opening import show_opening_sequence
from platinum.overworld import run_overworld
from platinum.audio.player import audio

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
        # Write to temporary save only; master is updated only on explicit Save
        save_temp(self.state)

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
    # If a save already exists, confirm deletion
    from platinum.system.save import list_saves
    saves = list_saves()
    if saves:
        print("A save for this game already exists. Are you SURE you want to delete it?")
        while True:
            resp = input("Type YES to delete, or NO to cancel (yes/no): ").strip().lower()
            if resp in {"yes","no","y","n"}:
                break
        if resp in {"no","n"}:
            print("Cancelled new game.")
            input("Press Enter to continue...")
            return
        # Delete existing saves
        try:
            import os
            for p in saves:
                try:
                    os.remove(p)
                except Exception:
                    pass
            # Also remove pointer files if present
            from pathlib import Path
            from platinum.system.save import _save_dir, LATEST_SYMLINK
            d = _save_dir()
            for nm in (LATEST_SYMLINK, "latest.xt"):
                fp = d / nm
                if fp.exists():
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            print("Previous saves deleted.")
        except Exception:
            print("Could not delete old saves; starting fresh state anyway.")
    # Fresh state & session start
    ctx.state = GameState()
    ctx.begin_session()
    # Capture current system time for day/night context
    from datetime import datetime
    now = datetime.now()
    ctx.state.system_time = now.strftime('%H:%M')
    hour = now.hour
    if 5 <= hour < 10:
        tod = 'morning'
    elif 10 <= hour < 18:
        tod = 'day'
    elif 18 <= hour < 22:
        tod = 'evening'
    else:
        tod = 'night'
    ctx.state.time_of_day = tod
    events = load_events()
    ctx.events.register_batch(events)
    
    # First ensure spawn location is set
    ctx.set_location("twinleaf_town_bedroom")
    
    # Then trigger Rowan monologue (game_start trigger) up through the prompt to introduce yourself
    # Start intro BGM
    try:
        audio.play_music("assets/audio/bgm/rowan_intro.ogg", loop=True)
    except Exception:
        pass
    ctx.suspend_autosave()
    try:
        ctx.events.dispatch_trigger({"type": "game_start"})
        # Immediately fire an enter_map trigger for the initial location so any
        # bedroom intro events (e.g., rival bursting in) occur without needing
        # the player to leave and re-enter.
        if ctx.state.location:
            ctx.events.dispatch_trigger({"type": "enter_map", "value": ctx.state.location})
    finally:
        ctx.resume_autosave(flush=True)
    # 2. Player self-identification (name + gender) prompted by Rowan
    # --- Mandatory player name (no blank allowed) ---
    while True:
        try:
            pn = input("Enter your name: ").strip()
        except EOFError:
            pn = ''
        if pn:
            break
        print("Name cannot be empty.")
    # --- Mandatory gender selection (M/F only) ---
    while True:
        try:
            gn_raw = input("Select gender (M/F): ").strip().lower()
        except EOFError:
            gn_raw = ''
        if gn_raw[:1] in ('m','f'):
            break
        print("Please enter M or F.")
    # Rival name (blank -> Barry)
    try:
        rn = input("Enter your rival's name [Barry]: ").strip()
    except EOFError:
        rn = ''
    ctx.state.player_name = pn
    ctx.state.player_gender = 'male' if gn_raw[:1] == 'm' else 'female'
    # Assistant selection per spec: M -> Dawn, F -> Lucas, otherwise Dawn
    ctx.state.assistant = derive_assistant(ctx.state.player_gender)
    ctx.state.rival_name = rn or 'Barry'

    # Show Rowan's follow-up lines acknowledging rival and sending you off
    try:
        ctx.dialogue.show("intro.start.5")
        ctx.dialogue.show("intro.start.6")
        ctx.dialogue.show("intro.start.7")
    except Exception:
        pass
    # Fade out intro BGM to transition into overworld
    try:
        audio.fadeout(800)
    except Exception:
        pass
    
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
    # Ensure events are loaded so story flags/triggers work in continued sessions
    events = load_events()
    ctx.events.register_batch(events)
    print(f"Loaded save for {gs.player_name} at {gs.location} (Badges: {len(gs.badges)})")
    # Drop straight into the overworld at the saved location
    run_overworld(ctx)

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
    # On app start, discard any leftover temp save (unsaved progress is lost by design)
    try:
        delete_temp()
    except Exception:
        pass
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
                # Ensure events are loaded before entering overworld
                if len(ctx.events.registry.events) == 0:
                    events = load_events()
                    ctx.events.register_batch(events)
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
            # Discard unsaved temp progress when quitting
            try:
                delete_temp()
            except Exception:
                pass
            break
    settings.save()

def derive_assistant(player_gender: str) -> str:
    # Male player -> Dawn; Female player -> Lucas
    return 'lucas' if player_gender == 'female' else 'dawn'

if __name__ == "__main__":
    run()