import sys
from typing import Any, Dict

from .system.settings import Settings
from .ui.typewriter import Typewriter
from .ui.opening import show_opening
from .ui.menu import show_main_menu, show_options_menu
from .ui.input import get_choice, get_input
from .ui.dialogue_manager import DialogueManager
from .events.loader import load_events
from .events.engine import EventEngine
from .config.flags import FlagStore
from .inventory import Inventory


class GameContext:
    """Context object passed to event scripts"""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.typewriter = Typewriter(settings.get("text_speed", 1.0))
        self.dialogue = DialogueManager(mode=settings.get("dialogue_mode", "expanded"))
        self.flags = FlagStore()
        self.inventory = Inventory()
        self.ui = GameUI(self.typewriter)
        self.event_engine = None  # Will be set by CLI
        self.battle_manager = BattlePlaceholder()
    
    def log(self, message: str):
        print(f"[LOG] {message}")


class GameUI:
    """UI wrapper for event scripts"""
    def __init__(self, typewriter: Typewriter):
        self.typewriter = typewriter
    
    def show_dialogue(self, speaker: str, text: str):
        """Display dialogue with speaker"""
        print(f"\n{speaker}:")
        self.typewriter.print(f"  {text}")
        input("  (Press Enter to continue)")
    
    def choose_starter(self, choices):
        """Let player choose a starter Pokemon"""
        print("\nChoose your starter Pokemon:")
        return get_choice("Which Pokemon will you choose?", choices)


class BattlePlaceholder:
    """Placeholder battle manager"""
    def start(self, battle_id: str, context: str = None):
        print(f"\n[BATTLE PLACEHOLDER]")
        print(f"Starting battle: {battle_id}")
        if context:
            print(f"Context: {context}")
        print("Battle system not yet implemented!")
        input("Press Enter to continue...")


def run():
    """Main entry point for the Pokemon Platinum CLI"""
    try:
        settings = Settings()
        ctx = GameContext(settings)
        
        # Load events
        registry = load_events()
        ctx.event_engine = EventEngine(registry, ctx)
        
        # Show opening
        show_opening(ctx.typewriter)
        
        # Main game loop
        while True:
            choice = show_main_menu()
            
            if choice == "New Game":
                start_new_game(ctx)
            elif choice == "Load Game":
                ctx.typewriter.print("Load game not yet implemented!")
                input("Press Enter to continue...")
            elif choice == "Options":
                handle_options(settings, ctx)
            elif choice == "Exit":
                print("Thanks for playing!")
                sys.exit(0)
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def start_new_game(ctx: GameContext):
    """Start a new game"""
    print("\n=== NEW GAME ===")
    ctx.typewriter.print("Starting your Pokemon adventure...")
    
    # Trigger the game start event
    ctx.event_engine.trigger("game_start")
    
    # Basic exploration loop placeholder
    print("\n[EXPLORATION STUB]")
    ctx.typewriter.print("You are now in the game world!")
    ctx.typewriter.print("Full exploration system coming in future updates.")
    input("Press Enter to return to main menu...")


def handle_options(settings: Settings, ctx: GameContext):
    """Handle options menu"""
    while True:
        choice = show_options_menu()
        
        if choice == "Dialogue Mode":
            configure_dialogue_mode(settings, ctx)
        elif choice == "Text Speed":
            configure_text_speed(settings, ctx)
        elif choice == "Back":
            break


def configure_dialogue_mode(settings: Settings, ctx: GameContext):
    """Configure dialogue mode setting"""
    print("\nDialogue Mode Options:")
    print("- base: Concise text")
    print("- expanded: Detailed descriptions") 
    print("- alt: Random variations")
    
    current = settings.get("dialogue_mode", "expanded")
    print(f"\nCurrent mode: {current}")
    
    modes = ["base", "expanded", "alt"]
    new_mode = get_choice("Choose dialogue mode:", modes, current)
    
    if new_mode != current:
        settings.set("dialogue_mode", new_mode)
        ctx.dialogue.set_mode(new_mode)
        print(f"Dialogue mode set to: {new_mode}")
    
    input("Press Enter to continue...")


def configure_text_speed(settings: Settings, ctx: GameContext):
    """Configure text speed setting"""
    print("\nText Speed Options:")
    speeds = {
        "Slow": 0.5,
        "Normal": 1.0,
        "Fast": 2.0,
        "Instant": 10.0
    }
    
    current_speed = settings.get("text_speed", 1.0)
    current_name = "Normal"
    for name, speed in speeds.items():
        if abs(speed - current_speed) < 0.1:
            current_name = name
            break
    
    print(f"Current speed: {current_name}")
    
    speed_names = list(speeds.keys())
    new_name = get_choice("Choose text speed:", speed_names, current_name)
    
    if new_name != current_name:
        new_speed = speeds[new_name]
        settings.set("text_speed", new_speed)
        ctx.typewriter.set_speed(new_speed)
        print(f"Text speed set to: {new_name}")
    
    input("Press Enter to continue...")