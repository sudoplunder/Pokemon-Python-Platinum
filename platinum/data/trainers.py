"""Trainer data loading system for JSON-based trainers."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class TrainerPokemon:
    """Individual Pokemon data for a trainer."""
    species_id: int
    level: int
    moves: List[str]
    requires_flag: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainerPokemon':
        return cls(
            species_id=data['species_id'],
            level=data['level'],
            moves=data.get('moves', []),
            requires_flag=data.get('requires_flag')
        )

@dataclass
class TrainerData:
    """Complete trainer data structure."""
    trainer_id: str
    name: str
    approach_dialogue: str
    loss_dialogue: str
    party: List[TrainerPokemon]
    money_won: int
    money_lost: int
    music: Optional[str] = None
    victory_music: Optional[str] = None
    
    @classmethod
    def from_dict(cls, trainer_id: str, data: Dict[str, Any]) -> 'TrainerData':
        party = [TrainerPokemon.from_dict(p) for p in data.get('party', [])]
        return cls(
            trainer_id=trainer_id,
            name=data['name'],
            approach_dialogue=data['approach_dialogue'],
            loss_dialogue=data['loss_dialogue'],
            party=party,
            money_won=data.get('money_won', 0),
            money_lost=data.get('money_lost', 0),
            music=data.get('music'),
            victory_music=data.get('victory_music')
        )

class TrainerLoader:
    """Loads and manages trainer data from JSON files."""
    
    def __init__(self):
        self.trainers: Dict[str, TrainerData] = {}
        self._load_all_trainers()
    
    def _load_all_trainers(self):
        """Load all trainer JSON files from assets/trainers/."""
        trainer_dir = Path("assets/trainers")
        if not trainer_dir.exists():
            return
        
        for json_file in trainer_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                trainer_id = json_file.stem
                trainer = TrainerData.from_dict(trainer_id, data)
                self.trainers[trainer_id] = trainer
                
            except Exception as e:
                print(f"[trainers] Failed to load {json_file}: {e}")
    
    def get_trainer(self, trainer_id: str) -> Optional[TrainerData]:
        """Get trainer data by ID."""
        return self.trainers.get(trainer_id)
    
    def list_trainers(self) -> List[str]:
        """Get list of all loaded trainer IDs."""
        return list(self.trainers.keys())

# Global trainer loader instance
_trainer_loader = None

def get_trainer(trainer_id: str) -> Optional[TrainerData]:
    """Get trainer data by ID (creates loader if needed)."""
    global _trainer_loader
    if _trainer_loader is None:
        _trainer_loader = TrainerLoader()
    return _trainer_loader.get_trainer(trainer_id)