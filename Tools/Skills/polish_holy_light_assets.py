"""Update the Holy Light visuals without reimporting its sound or icon."""
import runpy
from pathlib import Path
import unreal

runpy.run_path(str(Path(unreal.Paths.project_dir())/'Tools/Skills/build_holy_light_assets.py'),
              init_globals={'HOLY_VISUALS_ONLY':True})
