from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List
import random

@dataclass
class DialogueEntry:
    key: str
    speaker: Optional[str]
    text: str  # single unified dialogue text (formerly 'expanded')