from pathlib import Path
from datetime import datetime
import json,shutil,runpy,unreal as u
R=Path(__file__).resolve().parent;P=R.parent;PROJECT=P.parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world():raise RuntimeError('Finish play before updating district blueprints')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith('/Game/NativeNearBank20261028/') for p in dirty):raise RuntimeError('Preserve unsaved district content')
marker=R/'backup.json'
if not marker.exists():
 backup=P/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/'Performance';C=PROJECT/'Content';files=[C/'GameMaps/L_CyberpunkApartment.umap']+list((C/'NativeNearBank20261028/Blocks').glob('*.uasset'))
 for src in files:
  dst=backup/src.relative_to(C);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 marker.write_text(json.dumps(dict(path=str(backup),files=len(files)),indent=2))
shutil.copy2(R/'manifest.json',P/'publish_manifest.json')
runpy.run_path(str(P/'build_publish_assets.py'),run_name='__main__')
runpy.run_path(str(P/'install_level.py'),run_name='__main__')
receipt=json.loads((P/'installed.json').read_text());receipt.update(performance_policy='distance-and-proxy-20261028',performance_backup=json.loads(marker.read_text())['path'],gameplay_test=False,framerate_measured=False)
(R/'published.json').write_text(json.dumps(receipt,indent=2));(P/'installed.json').write_text(json.dumps(receipt,indent=2))
print('DISTRICT_PERFORMANCE_FORMAL_MAP_SAVED',receipt['instances'])
