from .characters import characters
from platinum.ui.dialogue_manager import DialogueManager  # runtime injection expected
def cmd_SHOW_TEXT(ctx, **kwargs):
    text_id = kwargs.get("text_id")
    speaker_key = kwargs.get("speaker","narration")
    speaker = characters.display(speaker_key)
    line = ctx.dialogue.resolve(text_id)
    ctx.ui.show_dialogue(speaker, line)
def cmd_GIVE_ITEM(ctx, **kwargs):
    item = kwargs["item"]; qty = kwargs.get("qty",1)
    ctx.inventory.add(item, qty)
    ctx.log(f"Received {item} x{qty}")
def cmd_SET_FLAG(ctx, **kwargs):
    flag = kwargs["flag"]; ctx.flags.set(flag, True)
def cmd_START_BATTLE(ctx, **kwargs):
    battle_id = kwargs["battle_id"]
    ctx.battle_manager.start(battle_id, context=kwargs.get("context"))
def cmd_STARTER_CHOICE(ctx, **kwargs):
    choices = kwargs["choices"]
    prefix = kwargs.get("assign_flag_prefix","starter.")
    chosen = ctx.ui.choose_starter(choices)
    ctx.flags.set(prefix+chosen, True)
    ctx.flags.set("player.starter", chosen)
def cmd_CALL_EVENT(ctx, **kwargs):
    event_id = kwargs["event_id"]; ctx.event_engine.invoke(event_id)
COMMAND_HANDLERS = {
    "SHOW_TEXT": cmd_SHOW_TEXT,
    "GIVE_ITEM": cmd_GIVE_ITEM,
    "SET_FLAG": cmd_SET_FLAG,
    "START_BATTLE": cmd_START_BATTLE,
    "STARTER_CHOICE": cmd_STARTER_CHOICE,
    "CALL_EVENT": cmd_CALL_EVENT
}
def execute_script(ctx, script):
    for command in script:
        handler = COMMAND_HANDLERS.get(command.cmd)
        if not handler:
            ctx.log(f"[WARN] Unknown command {command.cmd}")
            continue
        handler(ctx, **command.args)
