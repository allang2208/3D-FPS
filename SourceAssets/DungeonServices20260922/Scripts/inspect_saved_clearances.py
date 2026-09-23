"""Only the user's requested light/ceiling and structural-service inspection."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('read_scene.py','export_exact_geometry.py'):
    runpy.run_path(str(ROOT/'Scripts'/name),run_name='__main__',init_globals=dict(SCENE_SNAPSHOT='scene-after.json',EXPORT_SUFFIX='_after'))
