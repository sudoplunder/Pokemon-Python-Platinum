from __future__ import annotations
import os
from platinum.ui.logo import print_logo
from platinum.core.logging import logger

def show_opening():
    """Show the opening sequence, optionally skipping animation in minimal mode."""
    if os.environ.get('PLAT_MINIMAL_OPENING') == '1':
        print_logo()
        print("Fan-made educational reconstruction – Scope C foundation.")
        logger.info("Opening shown")
    else:
        # Import and run the full animated sequence
        from platinum.ui.opening_full import show_opening_sequence
        show_opening_sequence()