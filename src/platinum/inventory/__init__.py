class Inventory:
    def __init__(self): self._items = {}
    def add(self, item_id: str, qty: int=1):
        self._items[item_id] = self._items.get(item_id,0)+qty
    def remove(self, item_id: str, qty: int=1):
        if self._items.get(item_id,0)<qty: raise ValueError("Not enough items")
        self._items[item_id]-=qty
        if self._items[item_id]<=0: del self._items[item_id]
    def has(self, item_id: str, qty: int=1) -> bool:
        return self._items.get(item_id,0)>=qty
    def snapshot(self): return dict(self._items)
