"""Update only the three rear-grip static assets and private materials."""
import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'install.py'),init_globals={'ONLY_PARTS':('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip')})
runpy.run_path(str(O/'RearGripFinish/read_render_tangents.py'))
