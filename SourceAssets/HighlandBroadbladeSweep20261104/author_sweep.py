"""Bake the frame-tracked Highland sweep using its recorded per-grip fits."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'VideoFitV3/author_v3.py'),run_name='__main__')
