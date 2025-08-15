from platinum.system.settings import Settings
from platinum.cli import GameContext
from platinum.events.loader import load_events
from platinum.system.save import PartyMember
from platinum.battle.experience import required_exp_for_level
from platinum.events.types import Event


def test_experience_award_on_auto_battle(monkeypatch):
    settings = Settings.load()
    ctx = GameContext(settings)
    pm = PartyMember(species='turtwig', level=5, hp=20, max_hp=20, exp=required_exp_for_level(5))
    ctx.state.party.append(pm)
    evt = Event(
        id='exp_test_evt',
        trigger={'type':'manual'},
        actions=[{'command':'START_BATTLE','battle_id':'exp_test','enemy_species':396,'enemy_level':3,'trainer':False,'interactive':False}],
        once=False
    )
    ctx.events.registry.register(evt)
    ctx.events.dispatch_trigger({'type':'manual'})
    assert pm.exp >= required_exp_for_level(5)
    assert pm.level >= 5


def test_experience_award_on_interactive_sim(monkeypatch):
    settings = Settings.load()
    ctx = GameContext(settings)
    pm = PartyMember(species='turtwig', level=5, hp=20, max_hp=20, exp=required_exp_for_level(5))
    ctx.state.party.append(pm)
    import platinum.ui.battle as battle_ui
    def fake_run(session, is_trainer=False):
        # Knock out enemy active battler
        for b in session.enemy.members:
            b.current_hp = 0
        return 'PLAYER_WIN'
    monkeypatch.setattr(battle_ui, 'run_battle_ui', fake_run)
    evt2 = Event(
        id='exp_test_evt2',
        trigger={'type':'manual2'},
        actions=[{'command':'START_BATTLE','battle_id':'exp_test2','enemy_species':396,'enemy_level':3,'trainer':True,'interactive':True}],
        once=False
    )
    ctx.events.registry.register(evt2)
    ctx.events.dispatch_trigger({'type':'manual2'})
    assert pm.exp >= required_exp_for_level(5)
    assert pm.level >= 5
