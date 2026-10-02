"""Save the neutral-reference editable source in background Blender."""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
runpy.run_path("D:/FPS3D/FPSGAME/Tools/ModularOutfit/save_bare_family_blends.py", init_globals={
    "AUTHOR_ROOT": str(HERE), "NATIVE_SOURCE_ROOT": str(HERE / "NativeSources"),
    "FAMILY_VERSION": "V7NeutralLeftBind20261002",
})
