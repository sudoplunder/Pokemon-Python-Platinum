from __future__ import annotations
from typing import Any

def handle_show_text(ctx, action: dict):
    key = action.get("dialogue_key")
    if key:
        ctx.dialogue.render(key)

def handle_set_flag(ctx, action: dict):
    flag = action.get("flag")
    if flag:
        ctx.set_flag(flag)

def handle_clear_flag(ctx, action: dict):
    flag = action.get("flag")
    if flag:
        ctx.clear_flag(flag)

def handle_start_battle(ctx, action: dict):
    bid = action.get("battle_id", "unknown")
    print(f"[battle] (placeholder) Starting battle '{bid}' ...")
    print("[battle] (placeholder) Result: PLAYER_WIN")

COMMANDS = {
    "SHOW_TEXT": handle_show_text,
    "SET_FLAG": handle_set_flag,
    "CLEAR_FLAG": handle_clear_flag,
    "START_BATTLE": handle_start_battle
}

def run_action(ctx, action: dict):
    cmd = action.get("command")
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"[events] Unknown command: {cmd}")
        return
    fn(ctx, action)