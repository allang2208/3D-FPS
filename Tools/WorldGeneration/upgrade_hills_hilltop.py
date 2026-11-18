"""Authorized same-seed hilltop migration. Saves data only; never starts gameplay."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/HillsHilltopVillage20261117'
OUT.mkdir(parents=True,exist_ok=True)
slot='TemperateHills_World'
path=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir()))/'SaveGames'/(slot+'.sav')
if path.resolve()!=(ROOT/'Saved/SaveGames'/(slot+'.sav')).resolve():
    raise RuntimeError('Migration requires the actual project save directory')
original=path.read_bytes()
before_hash=hashlib.sha256(original).hexdigest()
save=u.GameplayStatics.load_game_from_slot(slot,0)
if not save or not isinstance(save,u.TemperateHillsSave):
    raise RuntimeError('The existing hills world could not be loaded; do not replace it')
previous={key:save.get_editor_property(key) for key in ('version','seed','generator_version')}
previous['world_id']=u.GuidLibrary.conv_guid_to_string(save.get_editor_property('world_id'))
previous['edits']=len(save.get_editor_property('edits'))
previous['craters']=len(save.get_editor_property('craters'))
if previous['version']>4 or previous['generator_version']>3:
    raise RuntimeError('A newer world format is already present')
backup=OUT/'Before/SaveGames'/('TemperateHills_World-'+before_hash[:12]+'.sav')
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_bytes(original)
save.set_editor_property('version',4)
save.set_editor_property('generator_version',3)
# Keep seed, world identity and saved edit records. Terrain destruction stays paused.
stage_slot='TemperateHills_HilltopUpgrade20261117'
if not u.GameplayStatics.save_game_to_slot(save,stage_slot,0):
    raise RuntimeError('Could not serialize the upgraded world')
stage=path.parent/(stage_slot+'.sav')
if path.read_bytes()!=original:
    raise RuntimeError('The world changed during serialization; original and staged saves retained')
os.replace(stage,path)
report={'saved':True,'same_seed':previous['seed'],'world_id':previous['world_id'],
        'previous':previous,'generator_version':3,'save_version':4,'backup':str(backup),
        'before_sha256':before_hash,'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'saved_at':datetime.now().astimezone().isoformat(),'gameplay_started':False,
        'rebuild_on_next_hills_entry':True}
(OUT/'world-migration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('HILLS_HILLTOP_SAVED '+json.dumps(report,ensure_ascii=False))
