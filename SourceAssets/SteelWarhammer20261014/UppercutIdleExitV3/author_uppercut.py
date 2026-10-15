"""Use the current right-arm uppercut revision."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent.parent/"UppercutRightAnatomyV7"/'author_uppercut.py'),run_name="__main__")
