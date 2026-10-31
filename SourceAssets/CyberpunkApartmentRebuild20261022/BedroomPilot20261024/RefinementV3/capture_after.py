from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'capture_geometry.py'),init_globals={'CAPTURE_PHASE':'after'})
