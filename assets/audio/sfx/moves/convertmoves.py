import os
import subprocess
import shutil

# === CONFIG ===
folder = r"C:\Users\paeri\Desktop\Pokemon-Python-Platinum\assets\audio\sfx\moves"
# Optional: hardcode your ffmpeg path if it's not on PATH, e.g.:
# ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
ffmpeg_path = shutil.which("ffmpeg")  # tries to find ffmpeg.exe on PATH

if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
    raise FileNotFoundError(
        "FFmpeg not found. Install it and ensure ffmpeg.exe is on your PATH, "
        "or set ffmpeg_path to the full path of ffmpeg.exe at the top of this script."
    )

# Create list of mp3 files (case-insensitive)
mp3_files = [f for f in os.listdir(folder) if f.lower().endswith(".mp3")]
if not mp3_files:
    print("No .mp3 files found in the folder.")
else:
    for filename in mp3_files:
        mp3_path = os.path.join(folder, filename)
        ogg_path = os.path.join(folder, os.path.splitext(filename)[0] + ".ogg")

        # FFmpeg command: convert MP3 -> OGG (Vorbis) at a reasonable quality
        # You can tweak -q:a (0=highest quality, 10=lowest). 5 is a good default.
        cmd = [
            ffmpeg_path,
            "-y",                     # overwrite output without asking
            "-hide_banner",
            "-loglevel", "error",     # only show errors
            "-i", mp3_path,
            "-c:a", "libvorbis",
            "-q:a", "5",
            ogg_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.isfile(ogg_path):
                # Delete original MP3 only if conversion succeeded
                os.remove(mp3_path)
                print(f"Converted and deleted: {filename} -> {os.path.basename(ogg_path)}")
            else:
                # Show ffmpeg's stderr to help debug issues (e.g., corrupted file)
                print(f"Error converting {filename}:\n{result.stderr.strip() or 'Unknown error'}")
        except Exception as e:
            print(f"Error converting {filename}: {e}")
