from __future__ import annotations
"""Lightweight placeholder overworld navigation.

Implements hierarchical location interaction menus:
- Bedroom -> actions: head downstairs, look at Wii, look at clock
- Downstairs -> actions: talk to mom, exit to Twinleaf Town, go back upstairs
- Twinleaf Town -> actions: enter your house, enter rival's house, north to Route 201

Sets game state location and can raise simple flags for future event triggers.
"""
from platinum.ui.menu_nav import select_menu

BEDROOM = "twinleaf_town_bedroom"
DOWNSTAIRS = "twinleaf_town_home_interior"
TWINLEAF = "twinleaf_town_outside"
ROUTE201 = "route_201_path"


def overworld_loop(ctx):
    while True:
        loc = ctx.state.location
        if loc == BEDROOM:
            if not _bedroom(ctx):
                break
        elif loc == DOWNSTAIRS:
            if not _downstairs(ctx):
                break
        elif loc == TWINLEAF:
            if not _twinleaf(ctx):
                break
        else:
            # Unknown location fallback
            ctx.set_location(BEDROOM)


def _bedroom(ctx) -> bool:
    choice = select_menu(
        f"LOCATION: Bedroom",
        [
            ("Head downstairs", "down"),
            ("Look at Wii", "wii"),
            ("Look at clock", "clock"),
            ("Exit (return to main menu)", "exit"),
        ],
        footer="↑/↓ or W/S • Enter to select • Esc to exit"
    )
    if choice in (None, "exit"):
        return False
    if choice == "down":
        ctx.set_location(DOWNSTAIRS)
    elif choice == "wii":
        print("It's a Wii. The system is a little dusty but still works.")
    elif choice == "clock":
        import datetime
        now = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"You adjust the clock. Current system time synced: {now}")
        ctx.set_flag("clock_synced")
    return True


def _downstairs(ctx) -> bool:
    choice = select_menu(
        f"LOCATION: Downstairs",
        [
            ("Talk to Mom", "mom"),
            ("Exit to Twinleaf Town", "outside"),
            ("Go upstairs", "up"),
            ("Exit (return to main menu)", "exit"),
        ],
        footer="↑/↓ or W/S • Enter to select • Esc to exit"
    )
    if choice in (None, "exit"):
        return False
    if choice == "mom":
        ctx.dialogue.show("intro.rival.intro") if ctx.has_flag("rival_introduced") else print("MOM: Have a nice day dear!")
    elif choice == "outside":
        ctx.set_location(TWINLEAF)
        ctx.set_flag("left_home")
    elif choice == "up":
        ctx.set_location(BEDROOM)
    return True


def _twinleaf(ctx) -> bool:
    choice = select_menu(
        f"LOCATION: Twinleaf Town",
        [
            ("Enter your house", "home"),
            ("Enter rival's house", "rival"),
            ("North to Route 201", "r201"),
            ("Exit (return to main menu)", "exit"),
        ],
        footer="↑/↓ or W/S • Enter to select • Esc to exit"
    )
    if choice in (None, "exit"):
        return False
    if choice == "home":
        ctx.set_location(DOWNSTAIRS)
    elif choice == "rival":
        print("Rival's house is currently locked (placeholder).")
    elif choice == "r201":
        ctx.set_location(ROUTE201)
        # Placeholder: immediately return to town for now
        print("(Route 201 area not yet implemented; returning to town.)")
        ctx.set_location(TWINLEAF)
    return True
