from __future__ import annotations
from platinum.ui.logo import print_logo
from platinum.core.logging import logger

def show_opening():
    print_logo()
    print("Fan-made educational reconstruction – Scope C foundation.")
    logger.info("Opening shown")