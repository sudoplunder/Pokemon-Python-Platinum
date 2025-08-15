"""Central audio engine (music + simple SFX) with graceful fallback.

Uses pygame.mixer if available; otherwise calls are no-ops (silent) so the
rest of the game logic does not crash when audio libs aren't installed.

Public singleton: ``audio``

Current surface API (intentionally small; expand as needed):
  audio.play_music(path: str, loop: bool = False)
  audio.fadeout(ms: int = 600)
  audio.stop_music()
  audio.set_music_volume(vol: float)   # 0.0 – 1.0

Notes:
  - Lazy initialization: mixer only initialized on first successful call.
  - Repeated play_music with the same path will restart; different path loads new.
  - Safe on systems without audio / pygame; failures logged (print) once.
"""

from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import threading

try:  # Optional logger
    from platinum.core.logging import logger as _logger
except Exception:  # pragma: no cover - fallback
    class _Fallback:
        def debug(self, *a, **k): print("[debug]", *a)
        def warn(self, *a, **k): print("[warn]", *a)
        def info(self, *a, **k): print("[info]", *a)
    _logger = _Fallback()


@dataclass
class _State:
    inited: bool = False
    failed: bool = False
    last_path: str | None = None


class AudioEngine:
    def __init__(self):
        self._state = _State()
        self._lock = threading.Lock()
        self._sfx_master = 1.0  # master multiplier for all SFX


    # --- internal -----------------------------------------------------
    def _ensure_init(self):
        if self._state.inited or self._state.failed:
            return
        with self._lock:
            if self._state.inited or self._state.failed:
                return
            try:
                import pygame  # type: ignore
                pygame.mixer.init()
                self._state.inited = True
                _logger.debug("AudioInitSuccess")
            except Exception as e:  # pragma: no cover - environment dependent
                self._state.failed = True
                _logger.warn("AudioInitFailed", error=str(e))

    def _mixer(self):  # helper
        if not self._state.inited:
            return None
        try:
            from pygame import mixer  # type: ignore
            return mixer
        except Exception:  # pragma: no cover
            return None

    # --- public -------------------------------------------------------
    def play_music(self, path: str | Path, loop: bool = False):
        p = Path(path)
        if not p.is_file():
            _logger.warn("AudioMissingFile", path=str(p))
            return
        self._ensure_init()
        if self._state.failed:
            return
        m = self._mixer()
        if not m:
            return
        try:
            if str(p) != self._state.last_path:
                m.music.load(str(p))
                self._state.last_path = str(p)
            m.music.play(-1 if loop else 0)
            _logger.debug("AudioPlayMusic", path=str(p), loop=loop)
        except Exception as e:  # pragma: no cover
            _logger.warn("AudioPlayFailed", path=str(p), error=str(e))

    def fadeout(self, ms: int = 600):
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.fadeout(ms)
                except Exception:
                    pass

    def stop_music(self):
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.stop()
                except Exception:
                    pass

    def set_music_volume(self, vol: float):
        vol = max(0.0, min(1.0, vol))
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.set_volume(vol)
                except Exception:
                    pass

    def set_sfx_master(self, vol: float):
        self._sfx_master = max(0.0, min(1.0, vol))

    def play_sfx(self, path: str | Path, volume: float | None = None):
        """Play a short sound effect (non-blocking).

        volume: optional per-call 0.0–1.0 scalar applied on top of master.
        """
        p = Path(path)
        if not p.is_file():
            _logger.warn("SFXMissingFile", path=str(p))
            return
        self._ensure_init()
        if self._state.failed:
            return
        m = self._mixer()
        if not m:
            return
        try:
            snd = m.Sound(str(p))  # type: ignore[attr-defined]
            final_vol = self._sfx_master
            if volume is not None:
                final_vol *= max(0.0, min(1.0, volume))
            try:
                snd.set_volume(final_vol)
            except Exception:
                pass
            snd.play()
            _logger.debug("SFXPlay", path=str(p))
        except Exception as e:  # pragma: no cover
            _logger.warn("SFXPlayFailed", path=str(p), error=str(e))


audio = AudioEngine()