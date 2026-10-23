"""Make the Yeal package importable for the tests (no install step)."""
import sys
from pathlib import Path

PYMODUL = Path(__file__).resolve().parents[1] / "BIN" / "versions" / "v0.1" / "PyModul"
if str(PYMODUL) not in sys.path:
    sys.path.insert(0, str(PYMODUL))
