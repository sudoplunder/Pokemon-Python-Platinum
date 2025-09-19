from __future__ import annotations
from pathlib import Path
from pydub import AudioSegment
from pydub.utils import which

"""Convert all .mp3 move SFX to .ogg in assets/audio/sfx/moves, then delete .mp3.

Requirements:
- pydub and ffmpeg must be installed and on PATH.
"""

def main() -> int:
    # Resolve moves folder relative to this script's location
    moves_dir = Path(__file__).resolve().parent / "moves"
    if not moves_dir.exists():
        print(f"Moves folder not found: {moves_dir}")
        return 1

    # Preflight: ensure ffmpeg/ffprobe are available; configure pydub explicitly
    ffmpeg_path = which("ffmpeg")
    ffprobe_path = which("ffprobe")
    if not ffmpeg_path or not ffprobe_path:
        print("ffmpeg/ffprobe not found. Please install ffmpeg and ensure it's on PATH, then re-run.")
        print("- Windows (winget): winget install ffmpeg")
        print("- Or download a static build and add its 'bin' folder to PATH.")
        return 1
    AudioSegment.converter = ffmpeg_path  # type: ignore[attr-defined]
    try:
        AudioSegment.ffprobe = ffprobe_path  # type: ignore[attr-defined]
    except Exception:
        pass

    mp3_files = sorted([p for p in moves_dir.glob("*.mp3")] + [p for p in moves_dir.glob("*.MP3")])
    if not mp3_files:
        print("No .mp3 files found to convert.")
        return 0

    converted = 0
    errors = 0
    for mp3_path in mp3_files:
        ogg_path = mp3_path.with_suffix(".ogg")
        try:
            # Load and export to OGG (overwrite if exists)
            audio = AudioSegment.from_file(str(mp3_path), format="mp3")
            audio.export(str(ogg_path), format="ogg")
            # Delete original only after successful export
            try:
                mp3_path.unlink()
            except Exception as e_del:
                print(f"Converted but could not delete MP3: {mp3_path.name} ({e_del})")
            print(f"Converted and deleted: {mp3_path.name} -> {ogg_path.name}")
            converted += 1
        except Exception as e:
            print(f"Error converting {mp3_path.name}: {e}")
            errors += 1

    print(f"\nDone. Converted: {converted} | Errors: {errors}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
