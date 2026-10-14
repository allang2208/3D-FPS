"""Reimport the repaired, task-owned mesh; existing map references remain valid."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Preserve active gameplay or unsaved maps')
item=next(m for m in json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes'] if m['kind']=='BreachConcrete')
asset=PROJECT/'Content'/(item['mesh'].removeprefix('/Game/')+'.uasset')
backup=ROOT/'Backups'/('concrete-asset-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
shutil.copy2(asset,backup/asset.name)
receipt=ROOT/'Receipts/install.json';shutil.copy2(receipt,backup/receipt.name)
runpy.run_path(str(ROOT/'install.py'))['import_mesh'](item)
report=json.loads(receipt.read_text('utf8'))
report['concrete_tangent_repair']=dict(saved=True,triangles=item['triangles'],backup=str(backup),source_sha256=item['sha256'])
receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('RECEPTION_CONCRETE_REPAIR_SAVED',item['mesh'])
