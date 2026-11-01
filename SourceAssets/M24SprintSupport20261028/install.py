"""Publish the three supported-sprint roles; retain all other live M24 work."""
import unreal as u,json,copy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;ACTIVE='/Game/Weapons/M24/MotionPolish20261027'
NAMES={'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}
patch=json.loads((O/'sprint_patch.json').read_text());expected=json.loads((O/'author_expected_profiles.json').read_text())
def packed(p,family):
 return {'family':family,'clips':[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[
 {'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]} for c in p.get_editor_property('clips')]}
targets=[ACTIVE+'/'+n for n in NAMES.values()]
if any(p.get_name() in targets for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
 raise RuntimeError('Unsaved M24 profile changes retained; publication stopped')
live={f:u.load_asset(ACTIVE+'/'+n) for f,n in NAMES.items()}
if any(p is None for p in live.values()):raise RuntimeError('Missing M24 profile')
before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
for family in NAMES:
 for role,replacement in patch.items():
  old=next(c for c in before[family]['clips'] if c['base']==replacement['base'])
  original=next(c for c in expected[family] if c['base']==replacement['base'])
  if old!=original:raise RuntimeError('Concurrent sprint change retained: '+family+'/'+role)
  dst=next(c for c in spec[family]['clips'] if c['base']==replacement['base']);dst.update(copy.deepcopy(replacement))
backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,name in NAMES.items():
 path=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset');dest=backup/(name+'.uasset')
 if not dest.exists():shutil.copy2(path,dest)
 p=backup/(name+'.json')
 if not p.exists():p.write_text(json.dumps(before[family]))
receipt={'complete':False,'saved':[],'roles':list(patch),'runtime_tested':False,'rendered':False,'native_build_required':False,'consumer':'M4TacticalSprintComponent -> FPSGunplayAnimInstance SprintProfile/SprintLoopProfile'}
for family,name in NAMES.items():
 if not live[family].set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Profile update failed '+name)
 if not u.EditorAssetLibrary.save_loaded_asset(live[family],False):raise RuntimeError('Profile save failed '+name)
 receipt['saved'].append(live[family].get_path_name());(O/(family+'_profile.json')).write_text(json.dumps(packed(live[family],family)))
 (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('M24_SUPPORTED_SPRINT_SAVED',len(receipt['saved']),flush=True)
