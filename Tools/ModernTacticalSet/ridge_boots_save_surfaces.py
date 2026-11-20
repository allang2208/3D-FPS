"""Import the TS01 boot PBR maps and save the eight UE material graphs."""
from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).with_name("exfil_reference_save_surfaces.py")),
    init_globals=dict(SURFACE_REVISION="RidgeBootsR2", SURFACE_PREFIX="RB_", SURFACE_TAG="RidgeBoot"),
    run_name="__main__",
)
