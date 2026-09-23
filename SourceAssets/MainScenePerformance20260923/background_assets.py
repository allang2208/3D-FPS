"""Run the authorized production edits in PythonScript commandlet; no game or preview."""
from pathlib import Path
import json, runpy
import unreal as u

ROOT=Path(__file__).parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
if not world:raise RuntimeError('Main map could not be loaded for production edits')
while True:
    runpy.run_path(str(ROOT/'apply_assets.py'),run_name='__main__')
    receipt=json.loads((ROOT/'Receipts/assets.json').read_text(encoding='utf-8'))
    if not receipt['remaining']:break
runpy.run_path(str(ROOT/'apply_scene.py'),run_name='__main__')
print('MAIN_SCENE_PRODUCTION_ASSETS_SAVED; no runtime tests executed')
