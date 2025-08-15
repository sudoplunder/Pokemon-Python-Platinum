from platinum.cli import GameContext
from platinum.system.settings import Settings
from platinum.system.save import PartyMember

def test_party_add_moves_to_box_when_full(tmp_path, monkeypatch):
    settings = Settings.load()
    ctx = GameContext(settings)
    # Fill party to 6
    for i in range(6):
        ctx.add_party_member(PartyMember(species=f"species{i}", level=5))
    assert len(ctx.state.party) == 6
    # Add 7th -> box
    target = ctx.add_party_member(PartyMember(species="species6", level=5))
    assert target == 'pc_box'
    assert len(ctx.state.party) == 6
    assert any(p.species == 'species6' for p in ctx.state.pc_box)

def test_party_cannot_drop_below_one(monkeypatch):
    settings = Settings.load()
    ctx = GameContext(settings)
    ctx.add_party_member(PartyMember(species="starter", level=5))
    # Attempt remove only member
    removed = ctx.remove_party_member(0)
    assert removed is False
    # Add second and remove first
    ctx.add_party_member(PartyMember(species="second", level=4))
    removed2 = ctx.remove_party_member(0)
    assert removed2 is True
    assert len(ctx.state.party) == 1
