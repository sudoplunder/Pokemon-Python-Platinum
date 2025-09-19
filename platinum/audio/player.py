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
import sys
import os
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
    loop_start: float | None = None
    loop_end: float | None = None
    loop_thread: threading.Thread | None = None
    stop_loop: bool = False


class AudioEngine:
    def __init__(self):
        self._state = _State()
        self._lock = threading.Lock()
        self._sfx_master = 1.0  # master multiplier for all SFX

    # --- path resolution (supports PyInstaller onefile) -----------------------
    def _resolve_path(self, path: str | Path) -> Path | None:
        """Resolve an asset path in dev and bundled (PyInstaller) modes.

        Priority:
        1) As given (absolute or relative to CWD)
        2) Next to the executable (exe_dir/path)
        3) PyInstaller temp dir (sys._MEIPASS/path)
        4) If the path (or its parents) contains an 'assets' segment, try
           exe_dir/assets/<tail-after-assets> and _MEIPASS/assets/<tail>.
        5) As fallback, try module root two levels up (for editable installs).
        """
        try:
            p = Path(path)
        except Exception:
            return None
        # 1) direct
        if p.is_file():
            return p
        # Common roots
        exe_dir = Path(getattr(sys, 'frozen', False) and Path(sys.executable).parent or os.getcwd())
        meipass = Path(getattr(sys, '_MEIPASS', '')) if hasattr(sys, '_MEIPASS') else None
        # 2) next to exe
        cand = exe_dir / p
        if cand.is_file():
            return cand
        # 3) under MEIPASS
        if meipass:
            cand = meipass / p
            if cand.is_file():
                return cand
        # 4) If path includes 'assets', reconstruct tail after assets
        parts = list(p.parts)
        if 'assets' in parts:
            try:
                idx = parts.index('assets')
                tail = Path(*parts[idx+1:]) if idx + 1 < len(parts) else Path()
                # exe_dir/assets/tail
                cand = exe_dir / 'assets' / tail
                if cand.is_file():
                    return cand
                if meipass:
                    cand = meipass / 'assets' / tail
                    if cand.is_file():
                        return cand
            except Exception:
                pass
        # 5) module root (repo layout) two parents up
        try:
            mod_root = Path(__file__).resolve().parents[2]
            cand = mod_root / p
            if cand.is_file():
                return cand
            if 'assets' in parts:
                idx = parts.index('assets')
                tail = Path(*parts[idx+1:]) if idx + 1 < len(parts) else Path()
                cand = mod_root / 'assets' / tail
                if cand.is_file():
                    return cand
        except Exception:
            pass
        return None


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

    def _stop_loop_thread(self):
        """Stop any running custom loop thread."""
        if self._state.loop_thread and self._state.loop_thread.is_alive():
            self._state.stop_loop = True
            self._state.loop_thread.join(timeout=1.0)
        self._state.stop_loop = False
        self._state.loop_thread = None

    def _play_music_standard(self, path: str, loop: bool):
        """Play music using standard pygame looping."""
        m = self._mixer()
        if not m:
            return
        try:
            if path != self._state.last_path:
                m.music.load(path)
                self._state.last_path = path
            m.music.play(-1 if loop else 0)
            _logger.debug("AudioPlayMusic", path=path, loop=loop)
        except Exception as e:  # pragma: no cover
            _logger.warn("AudioPlayFailed", path=path, error=str(e))
            # Simple fallback - try without any special handling
            pass

    def _play_music_with_custom_loop(self, path: str, loop_start: float | None, loop_end: float | None):
        """Play music with custom loop points using threading."""
        m = self._mixer()
        if not m:
            return
        
        try:
            if path != self._state.last_path:
                m.music.load(path)
                self._state.last_path = path
            
            # Play once first (non-looping)
            m.music.play(0)
            _logger.debug("AudioPlayMusicCustomLoop", path=path, loop_start=loop_start, loop_end=loop_end)
            
            # Start loop monitoring thread
            def loop_monitor():
                import time
                while not self._state.stop_loop:
                    if m and m.music.get_busy():
                        # Get current position (note: pygame doesn't provide this directly)
                        # For now, we'll use time-based estimation
                        time.sleep(0.1)
                    else:
                        # Song ended, restart from loop_start
                        if not self._state.stop_loop:
                            try:
                                # For simple implementation, restart the whole song
                                # In a more advanced version, you'd seek to loop_start
                                m.music.play(0)
                                if loop_start and loop_start > 0:
                                    # Skip ahead to loop start (rough implementation)
                                    time.sleep(loop_start)
                            except Exception:
                                break
                        break
            
            self._state.loop_thread = threading.Thread(target=loop_monitor, daemon=True)
            self._state.loop_thread.start()
            
        except Exception as e:  # pragma: no cover
            _logger.warn("AudioPlayCustomLoopFailed", path=path, error=str(e))
            # Fallback to standard looping
            self._play_music_standard(path, True)

    # --- public -------------------------------------------------------
    def play_music(self, path: str | Path, loop: bool = False, loop_start: float | None = None, loop_end: float | None = None):
        """Play music with optional custom loop points.
        
        Args:
            path: Path to the music file
            loop: Whether to loop the music
            loop_start: Loop start time in seconds (Note: Limited pygame support)
            loop_end: Loop end time in seconds (Note: Limited pygame support)
            
        Note: Custom loop points are experimental due to pygame limitations.
        For best results, pre-process audio files with proper loop points.
        """
        rp = self._resolve_path(path)
        if not rp or not rp.is_file():
            _logger.warn("AudioMissingFile", path=str(path))
            return
        self._ensure_init()
        if self._state.failed:
            return
        m = self._mixer()
        if not m:
            return
        
        # Stop any existing loop thread
        self._stop_loop_thread()
        
        # For now, log custom loop points but use standard looping
        # pygame.mixer.music has significant limitations for custom loop points
        if loop_start is not None or loop_end is not None:
            _logger.info("CustomLoopPointsRequested", path=str(rp), start=loop_start, end=loop_end, 
                        note="Using standard looping due to pygame limitations")
        
        # Use standard pygame looping (reliable)
        self._play_music_standard(str(rp), loop)

    def play_intro_loop_music(self, intro_path: str | Path, loop_path: str | Path):
        """Play intro music followed by looping background music.
        
        This is ideal for game music that has a distinct intro followed by a seamless loop.
        The intro plays once, then the loop section plays indefinitely.
        
        Args:
            intro_path: Path to the intro audio file
            loop_path: Path to the looping audio file
        """
        intro_rp = self._resolve_path(intro_path)
        loop_rp = self._resolve_path(loop_path)
        
        if not intro_rp or not intro_rp.is_file():
            _logger.warn("AudioMissingIntroFile", path=str(intro_path))
            # Fallback to just playing the loop
            if loop_rp and loop_rp.is_file():
                self.play_music(loop_path, loop=True)
            return
            
        if not loop_rp or not loop_rp.is_file():
            _logger.warn("AudioMissingLoopFile", path=str(loop_path))
            # Fallback to just playing the intro without looping
            self.play_music(intro_path, loop=False)
            return
        
        self._ensure_init()
        if self._state.failed:
            return
        m = self._mixer()
        if not m:
            return
        
        # Stop any existing music/threads
        self._stop_loop_thread()
        
        try:
            # Play intro first (non-looping)
            m.music.load(str(intro_rp))
            self._state.last_path = str(intro_rp)
            m.music.play(0)
            _logger.debug("AudioPlayIntroLoop", intro=str(intro_rp), loop=str(loop_rp))
            
            # Set up thread to monitor intro completion and start loop
            def intro_loop_monitor():
                import time
                # Wait for intro to finish
                while not self._state.stop_loop:
                    if m and m.music.get_busy():
                        time.sleep(0.1)
                    else:
                        break
                
                # Start the loop section if we haven't been stopped
                if not self._state.stop_loop and m:
                    try:
                        m.music.load(str(loop_rp))
                        self._state.last_path = str(loop_rp)
                        m.music.play(-1)  # Loop indefinitely
                        _logger.debug("AudioStartLoop", path=str(loop_rp))
                    except Exception as e:
                        _logger.warn("AudioLoopStartFailed", path=str(loop_rp), error=str(e))
            
            self._state.loop_thread = threading.Thread(target=intro_loop_monitor, daemon=True)
            self._state.loop_thread.start()
            
        except Exception as e:  # pragma: no cover
            _logger.warn("AudioIntroLoopFailed", intro=str(intro_rp), loop=str(loop_rp), error=str(e))
            # Fallback to standard music
            self.play_music(loop_path, loop=True)

    def fadeout(self, ms: int = 600):
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.fadeout(ms)
                except Exception:
                    pass

    def stop_music(self):
        # Stop any custom loop thread first
        self._stop_loop_thread()
        
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

    def pause_music(self):
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.pause()
                except Exception:
                    pass

    def resume_music(self):
        if self._state.inited and not self._state.failed:
            m = self._mixer()
            if m:
                try:
                    m.music.unpause()
                except Exception:
                    pass

    def set_sfx_master(self, vol: float):
        self._sfx_master = max(0.0, min(1.0, vol))

    def play_sfx(self, path: str | Path, volume: float | None = None):
        """Play a short sound effect (non-blocking).

        volume: optional per-call 0.0–1.0 scalar applied on top of master.
        """
        rp = self._resolve_path(path)
        if not rp or not rp.is_file():
            _logger.warn("SFXMissingFile", path=str(path))
            return
        self._ensure_init()
        if self._state.failed:
            return
        m = self._mixer()
        if not m:
            return
        try:
            snd = m.Sound(str(rp))  # type: ignore[attr-defined]
            final_vol = self._sfx_master
            if volume is not None:
                final_vol *= max(0.0, min(1.0, volume))
            try:
                snd.set_volume(final_vol)
            except Exception:
                pass
            snd.play()
            _logger.debug("SFXPlay", path=str(rp))
        except Exception as e:  # pragma: no cover
            _logger.warn("SFXPlayFailed", path=str(rp), error=str(e))

    def play_sfx_blocking(self, path: str | Path, volume: float | None = None):
        """Play a short sound effect and block until it completes.

        Skips waiting under pytest to avoid slowing tests.
        Returns the duration in seconds if known, else None.
        """
        rp = self._resolve_path(path)
        if not rp or not rp.is_file():
            _logger.warn("SFXMissingFile", path=str(path))
            return None
        self._ensure_init()
        if self._state.failed:
            return None
        m = self._mixer()
        if not m:
            return None
        try:
            snd = m.Sound(str(rp))  # type: ignore[attr-defined]
            final_vol = self._sfx_master
            if volume is not None:
                final_vol *= max(0.0, min(1.0, volume))
            try:
                snd.set_volume(final_vol)
            except Exception:
                pass
            length = None
            try:
                length = float(snd.get_length())  # type: ignore[attr-defined]
            except Exception:
                length = None
            snd.play()
            _logger.debug("SFXPlayBlocking", path=str(rp), seconds=length or -1)
            try:
                import os, time
                if not os.getenv('PYTEST_CURRENT_TEST') and length:
                    time.sleep(length)
            except Exception:
                pass
            return length
        except Exception as e:  # pragma: no cover
            _logger.warn("SFXPlayFailed", path=str(rp), error=str(e))
            return None


audio = AudioEngine()