from pathlib import Path
import json,runpy
R=Path(__file__).resolve().parent
module=runpy.run_path(str(R/'build_assets.py'))
module['report'].update(json.loads((R/'assets_saved.json').read_text()))
module['meshes'](['Roads'])
print('AP16_ROAD_TURNAROUNDS_SAVED')
