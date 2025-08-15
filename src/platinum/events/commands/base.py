from __future__ import annotations
from typing import Protocol, Dict, Any

class ICommand(Protocol):
    name: str
    def execute(self, ctx, action: Dict[str, Any]) -> None: ...

class CommandRegistry:
    def __init__(self):
        self._cmds: dict[str, ICommand] = {}

    def register(self, cmd: ICommand):
        self._cmds[cmd.name] = cmd

    def get(self, name: str) -> ICommand | None:
        return self._cmds.get(name)

registry = CommandRegistry()