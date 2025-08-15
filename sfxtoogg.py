import os
from pydub import AudioSegment

# Path to your moves folder
moves_dir = r"C:\Users\paeri\Desktop\Pokemon-Python-Platinum\assets\audio\sfx\moves"

# Walk through the directory
for filename in os.listdir(moves_dir):
    if filename.lower().endswith(".mp3"):
        full_path = os.path.join(moves_dir, filename)

        # Convert filename to lowercase and change extension to .ogg
        new_filename = os.path.splitext(filename.lower())[0] + ".ogg"
        new_path = os.path.join(moves_dir, new_filename)

        print(f"Converting {filename} -> {new_filename}")

        # Load and convert
        mp3_audio = AudioSegment.from_mp3(full_path)
        mp3_audio.export(new_path, format="ogg")

        # Remove the original .mp3 file
        os.remove(full_path)

print("All MP3 files converted to OGG and renamed to lowercase.")
