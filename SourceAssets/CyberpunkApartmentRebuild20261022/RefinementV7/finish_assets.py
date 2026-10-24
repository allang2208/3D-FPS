"""Publish the final surfaces, geometry and city reflection after the first asset pass."""
from pathlib import Path
import runpy,traceback
R=Path(__file__).resolve().parent
d=runpy.run_path(str(R/'build_assets.py'))
d['report'].update(d['previous'])
d['report']['stage']='building';d['report'].pop('error',None);d['record']()
try:
 d['report']['textures']=[]
 d['import_textures']()
 d['build_belt']()
 d['glass']()
 d['meshes']()
 d['water']()
 d['report']['stage']='assets_saved';d['record']()
except Exception:
 d['report']['stage']='failed';d['report']['error']=traceback.format_exc();d['record']();raise
print('AP7_REMAINING_MESHES_SAVED')
