"""Repair the saved assembly root; preserve the existing shore and apartment."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,unreal as u
R=Path(__file__).resolve().parent
old=R.parent/'CyberpunkNearBank20261028'
project=R.parents[1]
backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
assets=json.loads((old/'assets_saved.json').read_text())
for row in assets['blueprints'].values():
    package=row['path'].split('.')[0]
    src=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
    dst=backup/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
author=runpy.run_path(str(old/'build_assets.py'))
author['assemblies']()
installer=runpy.run_path(str(old/'install_level.py'))
installer['main']()
(R/'foliage_repair_saved.json').write_text(json.dumps({'stage':'saved','blueprints':list(assets['blueprints']),'reason':'Explicit authored static SceneComponent root replaces auto DefaultSceneRoot; HISM components reattached before compile.','backup':str(backup),'map':'/Game/GameMaps/L_CyberpunkApartment','game_run':False},indent=2),encoding='utf8')
print('FOLIAGE_ROOT_REPAIR_SAVED',flush=True)
