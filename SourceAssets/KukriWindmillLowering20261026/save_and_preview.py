"""Save the new candidate, then read its compressed poses for the requested GIF."""
import runpy
from pathlib import Path
out=Path(__file__).resolve().parent
runpy.run_path(str(out/'save_all.py'))
runpy.run_path(str(out/'read_preview.py'))
