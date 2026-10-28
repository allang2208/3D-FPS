"""Read the relevant material/culling settings, then author and save V18."""
import runpy
from pathlib import Path
import unreal as u

folder = Path(u.Paths.project_dir()) / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoImpactV18'
runpy.run_path(str(folder / 'inspect_materials.py'), run_name='__main__')
runpy.run_path(str(folder / 'mountain_echo_impact_v18.py'), run_name='__main__')
