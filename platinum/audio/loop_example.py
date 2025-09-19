"""Example usage of custom loop points for BGM.

This shows how to use the enhanced audio system with loop points.
Loop points can be defined in JSON files alongside the audio files.
"""

import json
from pathlib import Path
from platinum.audio.player import audio

def load_loop_points(audio_path: str) -> tuple[float | None, float | None]:
    """Load loop start/end points from a .loop.json file.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Tuple of (loop_start, loop_end) in seconds, or (None, None) if no file found
        
    Example loop file (route_201.loop.json):
    {
        "loop_start": 5.2,
        "loop_end": 45.8,
        "description": "Route 201 theme - loops from intro end to outro start"
    }
    """
    audio_file = Path(audio_path)
    loop_file = audio_file.with_suffix('.loop.json')
    
    if not loop_file.exists():
        return None, None
    
    try:
        with open(loop_file, 'r') as f:
            data = json.load(f)
        return data.get('loop_start'), data.get('loop_end')
    except Exception:
        return None, None

def play_bgm_with_loops(audio_path: str):
    """Play BGM with custom loop points if available.
    
    Note: Due to pygame limitations, this currently falls back to standard looping.
    For true custom loop points, use the audio_loop_processor tool to create
    pre-processed audio files with proper loop sections.
    """
    loop_start, loop_end = load_loop_points(audio_path)
    
    if loop_start is not None or loop_end is not None:
        print(f"Loop points found for {audio_path}: {loop_start}s - {loop_end}s")
        print("Note: Using standard looping due to pygame limitations")
        # Still pass the loop points for logging, but they won't be used
        audio.play_music(audio_path, loop=True, loop_start=loop_start, loop_end=loop_end)
    else:
        print(f"Playing {audio_path} with standard looping")
        audio.play_music(audio_path, loop=True)

# Example usage:
if __name__ == "__main__":
    # This would play Route 201 music with custom loop points if the .loop.json file exists
    play_bgm_with_loops("assets/audio/bgm/route_201.ogg")