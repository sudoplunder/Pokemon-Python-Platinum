"""
Battle system package (currently a stub).
Future modules:
- models.py (Pokemon, Move, Stats, Status)
- mechanics.py (damage calc, accuracy, crits, STAB, type matchups)
- ai.py (opponent decision logic)
- render.py (HP bars, status display, color)
- actions.py (turn resolution pipeline)
"""
from .service import battle_service
__all__ = ["battle_service"]