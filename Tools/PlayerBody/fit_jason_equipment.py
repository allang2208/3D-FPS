"""Author the shared Jason garments; backpack authoring has a separate owner."""
import runpy
from pathlib import Path

PROJECT = Path("D:/FPS3D/FPSGAME")
runpy.run_path(str(PROJECT / "Tools/PlayerBody/fit_jason_outfits.py"), run_name="__main__")
print("JASON_GARMENTS_FITTED; backpack pipeline: Tools/BackpackHarness/author.py", flush=True)
