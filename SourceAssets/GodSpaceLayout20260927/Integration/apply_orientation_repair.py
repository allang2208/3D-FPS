"""Reapply the owned layout with named Rotator fields; persist the spawn repair."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('End current PIE before persisting the orientation repair')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve existing unsaved map changes')
source=PROJECT/'Content/GameMaps/DayNight_Lighting.umap'
backup=PROJECT/'trash/godspace-spawn-rotation-20260927/Before/Content/GameMaps/DayNight_Lighting.umap'
if not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    (ROOT/'Receipts/rotation-backup.json').write_text(json.dumps({'source':str(source),'backup':str(backup),'sha256':hashlib.sha256(backup.read_bytes()).hexdigest()},indent=2))
script=ROOT/'apply_map.py'
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script)})
report=json.loads((ROOT/'Receipts/map.json').read_text(encoding='utf8'))
report['repair']='Python Rotator positional order is roll,pitch,yaw; use explicit pitch=0,yaw=heading,roll=0 for PlayerStart, anchors and modular geometry.'
report['runtime_tested']=False
(ROOT/'Receipts/rotation-map.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('GODSPACE_ORIENTATION_REPAIR_SAVED')
