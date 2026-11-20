"""Import the field trouser surface textures and create their UE cloth materials."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("exfil_reference_save_surfaces.py")),
               init_globals=dict(SURFACE_REVISION="FieldTrousersR2",SURFACE_PREFIX="FT_",SURFACE_TAG="FieldTrousers"),
               run_name="__main__")
