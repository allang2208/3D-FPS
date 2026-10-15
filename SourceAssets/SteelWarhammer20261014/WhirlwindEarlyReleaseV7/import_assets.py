"""Import the current wider-inertia whirlwind animation."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent.parent/"WhirlwindInertiaV8/import_assets.py"),run_name="__main__")
