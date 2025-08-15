import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.platinum.cli import run

if __name__ == "__main__":
    run()