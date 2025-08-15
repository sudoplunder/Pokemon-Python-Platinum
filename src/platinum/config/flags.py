class FlagStore:
    def __init__(self): self._flags = {}
    def set(self, flag: str, value: bool=True): self._flags[flag]=value
    def get(self, flag: str) -> bool: return self._flags.get(flag, False)
    def snapshot(self): return dict(self._flags)
