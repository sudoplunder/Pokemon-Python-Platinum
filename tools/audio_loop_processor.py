"""Audio loop preprocessing tool.

Since pygame has limitations with custom loop points, this tool helps create
properly looped audio files by extracting and repeating the loop section.

Requirements: pydub (pip install pydub)
"""

import json
from pathlib import Path

def create_looped_audio(input_path: str, output_path: str, loop_json_path: str):
    """Create a properly looped audio file from loop point metadata.
    
    Args:
        input_path: Original audio file
        output_path: Where to save the looped version
        loop_json_path: JSON file with loop points
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub not installed. Run: pip install pydub")
        return False
    
    # Load loop points
    try:
        with open(loop_json_path, 'r') as f:
            loop_data = json.load(f)
        loop_start = loop_data.get('loop_start', 0) * 1000  # Convert to milliseconds
        loop_end = loop_data.get('loop_end') * 1000 if loop_data.get('loop_end') else None
    except Exception as e:
        print(f"Error reading loop file: {e}")
        return False
    
    # Load audio
    try:
        audio = AudioSegment.from_file(input_path)
    except Exception as e:
        print(f"Error loading audio: {e}")
        return False
    
    # Extract sections
    intro = audio[:int(loop_start)]
    
    if loop_end:
        loop_section = audio[int(loop_start):int(loop_end)]
    else:
        loop_section = audio[int(loop_start):]
    
    # Create looped version (intro + loop section repeated)
    # For game music, usually 2-3 repetitions are enough for seamless feel
    looped_audio = intro + loop_section + loop_section
    
    # Export
    try:
        looped_audio.export(output_path, format="ogg")
        print(f"Created looped audio: {output_path}")
        print(f"Intro: {len(intro)/1000:.1f}s, Loop: {len(loop_section)/1000:.1f}s")
        return True
    except Exception as e:
        print(f"Error exporting: {e}")
        return False

def create_seamless_loop(input_path: str, output_path: str, loop_json_path: str):
    """Create a seamless loop by crossfading the loop boundaries."""
    try:
        from pydub import AudioSegment
    except ImportError:
        print("Error: pydub not installed. Run: pip install pydub")
        return False
    
    # Load loop points and audio
    with open(loop_json_path, 'r') as f:
        loop_data = json.load(f)
    
    audio = AudioSegment.from_file(input_path)
    loop_start = int(loop_data.get('loop_start', 0) * 1000)
    loop_end = int(loop_data.get('loop_end', len(audio)/1000) * 1000)
    
    # Extract loop section
    loop_section = audio[loop_start:loop_end]
    
    # Create crossfade for seamless loop (100ms crossfade)
    crossfade_duration = 100
    loop_with_crossfade = loop_section.append(loop_section[:crossfade_duration], crossfade=crossfade_duration)
    
    # Final audio: intro + seamless loop
    final_audio = audio[:loop_start] + loop_with_crossfade
    
    final_audio.export(output_path, format="ogg")
    print(f"Created seamless loop: {output_path}")
    return True

# Example usage
if __name__ == "__main__":
    # Create a properly looped version of Route 201
    input_file = "assets/audio/bgm/route_201.ogg"
    output_file = "assets/audio/bgm/route_201_looped.ogg"
    loop_file = "assets/audio/bgm/route_201.loop.json"
    
    if Path(input_file).exists() and Path(loop_file).exists():
        create_seamless_loop(input_file, output_file, loop_file)
    else:
        print("Files not found. Make sure route_201.ogg and route_201.loop.json exist.")