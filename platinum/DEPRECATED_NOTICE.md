# DEPRECATED: Legacy Code Location

**This directory (`platinum/`) is deprecated and will be removed in a future release.**

## Migration Notice

The code in this directory has been migrated to `src/platinum/` to follow Python packaging best practices and avoid import shadowing issues.

### Key Changes:
- **Advanced opening sequence**: Moved from `platinum/ui/opening.py` to `src/platinum/ui/opening_full.py`
- **Event system**: Consolidated into `src/platinum/events/` with expanded command set
- **Core systems**: Now centralized in `src/platinum/game/context.py` with unified state management
- **Battle system**: Full implementation in `src/platinum/battle/` with MVP features
- **World layer**: New scaffolding in `src/platinum/world/` for locations and encounters

### How to Update:
Replace any imports from `platinum.*` with `src.platinum.*` or use the new main entry point:

```python
# Old (deprecated)
from platinum.cli import run

# New (recommended) 
from src.platinum.cli import run
```

### Environment Variables:
- `PLAT_MINIMAL_OPENING=1` - Skip animated opening sequence
- `PLAT_COLOR_DISABLED=1` - Disable ANSI colors
- `PLAT_RNG_SEED=<number>` - Set deterministic RNG seed

### Main Entry Point:
Use `python main.py` which now imports from the new location.

---

**Do not add new features to this deprecated directory.** 
**All active development should use `src/platinum/`.**