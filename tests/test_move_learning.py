from platinum.system.settings import Settings
from platinum.cli import GameContext
from platinum.system.save import PartyMember
from platinum.events.types import Event
from platinum.battle.experience import apply_experience, required_exp_for_level
from platinum.data.species_lookup import species_id


def test_move_learning_on_level(monkeypatch):
    # Use low-level species (Turtwig 387) and force learnset mock
    sid = species_id('turtwig')
    settings = Settings.load()
    ctx = GameContext(settings)
    pm = PartyMember(species='turtwig', level=5, exp=required_exp_for_level(5)-1, moves=['tackle'])
    ctx.state.party.append(pm)
    # Monkeypatch learnset to ensure new moves at level 6
    import platinum.data.loader as loader
    orig = loader.level_up_learnset
    def fake_learnset(species_id):
        return [ {'level':1,'name':'tackle'}, {'level':6,'name':'razor-leaf'}, {'level':6,'name':'withdraw'} ]
    monkeypatch.setattr(loader, 'level_up_learnset', fake_learnset)
    # Apply enough exp to cross into level 6
    res = apply_experience(pm, required_exp_for_level(6)-pm.exp, species_id=sid)
    assert res['leveled']
    assert pm.level >= 6
    assert any(m in pm.moves for m in ['razor-leaf','withdraw'])
    monkeypatch.setattr(loader, 'level_up_learnset', orig)
