from __future__ import annotations
from platinum.system.settings import Settings
from platinum.core.logging import logger
from platinum.dialogue.manager import DialogueManager
from platinum.events.loader import load_events
from platinum.events.engine import EventEngine
from platinum.battle.service import battle_service
from platinum.ui.menu import main_menu, options_submenu
from platinum.ui.opening import show_opening_sequence

class GameContext:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.flags: set[str] = set()
        self.dialogue = DialogueManager(settings)
        self.events = EventEngine(self)
        self.battle_service = battle_service

    def set_flag(self, flag: str):
        if flag not in self.flags:
            self.flags.add(flag)
            self.events.on_flag_set(flag)

    def clear_flag(self, flag: str):
        if flag in self.flags:
            self.flags.remove(flag)

    def debug_flags(self):
        return sorted(self.flags)

def start_new_game(ctx: GameContext):
    print("\n== New Game ==\n")
    events = load_events()
    ctx.events.register_batch(events)
    ctx.events.dispatch({"type":"game_start"})

def run():
    settings = Settings.load()
    # Defensive fallback if old settings file lacked log_level
    log_level = getattr(settings.data, "log_level", "INFO")
    from platinum.core.logging import logger as global_logger
    global_logger.set_level(log_level)
    ctx = GameContext(settings)
    show_opening_sequence()
    while True:
        choice = main_menu()
        if choice == "new":
            start_new_game(ctx)
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