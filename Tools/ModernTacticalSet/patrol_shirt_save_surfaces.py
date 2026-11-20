"""Save the combat shirt's PBR textures and native cloth materials."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("exfil_reference_save_surfaces.py")),
               init_globals=dict(SURFACE_REVISION="PatrolShirtR2", SURFACE_PREFIX="PS_", SURFACE_TAG="PatrolShirt"),
               run_name="__main__")
