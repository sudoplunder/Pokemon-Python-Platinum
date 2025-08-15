"""
Error classes for clearer exception sources.
"""
from __future__ import annotations

class PlatinumError(Exception):
    pass

class DataLoadError(PlatinumError):
    def __init__(self, path: str, detail: str):
        super().__init__(f"Failed to load {path}: {detail}")
        self.path = path
        self.detail = detail

class ValidationError(PlatinumError):
    pass

class CommandExecutionError(PlatinumError):
    def __init__(self, command: str, detail: str):
        super().__init__(f"Command '{command}' failed: {detail}")
        self.command = command
        self.detail = detail