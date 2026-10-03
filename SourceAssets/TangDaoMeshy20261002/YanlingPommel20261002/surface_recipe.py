"""Current Yanling pommel entrypoint: octagonal cone V3."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent / "ConeV3" / "surface_recipe.py"),run_name="__main__")
