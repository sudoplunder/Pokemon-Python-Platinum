# Ensure project root is on sys.path for tests
import sys, pathlib
root = pathlib.Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
