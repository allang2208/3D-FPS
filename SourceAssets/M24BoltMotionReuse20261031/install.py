"""Merge the copied bolt-cycle presentation only into its two target windows."""
import unreal as u,json,gzip,ast,copy,shutil,math,bisect
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary
before=json.load(gzip.open(O/'before.json.gz','rt'));patch=json.load(gzip.open(O/'bolt_motion_patch.json.gz','rt'))
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('packed','qlerp','sample'):exec(compile(ast.unparse(n),n.name,'exec'))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is active; finish the play session before saving these profiles')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in before['paths'].values()):raise RuntimeError('Unsaved profile changes retained')
identity=[0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]
staged={};live={};backup=O/'Before';backup.mkdir(exist_ok=True)
for family,path in before['paths'].items():
 asset=u.load_asset(path);live[family]=asset
 if not asset:raise RuntimeError('Missing '+path)
 if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):raise RuntimeError('Retained animation added; live profile retained')
 spec=packed(asset,family)
 fire=next(c for c in spec['clips'] if c['base'].endswith('A_M24_fire'))
 prior_fire=next(c for c in before['profiles'][family]['clips'] if c['base']==fire['base'])
 if next((t for t in fire['tracks'] if t['bone']=='WPN_root'),None)!=next((t for t in prior_fire['tracks'] if t['bone']=='WPN_root'),None):
  raise RuntimeError('Fire-cycle donor motion changed during authoring: '+family)
 original_spec=copy.deepcopy(spec)
 for change in patch[family]:
  dst=next(c for c in spec['clips'] if c['base']==change['base']);expected=next(c for c in before['profiles'][family]['clips'] if c['base']==change['base'])
  if dst['duration']!=expected['duration']:raise RuntimeError('Action timing changed during authoring: '+family)
  start,end=change['window']
  for replacement in change['tracks']:
   n=replacement['bone'];old=next((t for t in dst['tracks'] if t['bone']==n),None);prior=next((t for t in expected['tracks'] if t['bone']==n),None)
   if old!=prior:raise RuntimeError('Concurrent owned-track change retained: '+family+'/'+n)
   baseline=old or {'bone':n,'times':[0.,dst['duration']],'values':identity*2}
   times=list(baseline['times'])
   for t in replacement['times']:
    if all(abs(t-v)>1e-6 for v in times):times.append(t)
   times.sort();values=[];last=None
   for t in times:
    original=sample(baseline,t,10,'values');v=list(original)
    if start+1e-6<t<end-1e-6:
     v=sample(replacement,t,10,'values');v[7:10]=original[7:10]
    if last is not None and sum(x*y for x,y in zip(last,v[3:7]))<0:v[3:7]=[-x for x in v[3:7]]
    last=v[3:7];values.extend(v)
   merged={'bone':n,'times':times,'values':values}
   if old is None:dst['tracks'].append(merged)
   else:old.update(merged)
 staged[family]=spec
 dest=backup/(family+'.json.gz')
 if not dest.exists():
  with gzip.open(dest,'wt') as f:json.dump(original_spec,f)
 disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
 if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
R={'complete':False,'saved':[],'scope':'equip and empty reload bolt-cycle motion in four attachment profiles','cpp_changed':False,'mechanical_timing_changed':False,'runtime_tested':False}
for family,asset in live.items():
 if not asset.set_shared_clips_from_json(json.dumps(staged[family])):raise RuntimeError('Merge failed '+family)
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+family)
 R['saved'].append(asset.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
R['complete']=True;(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
print('M24_BOLT_MOTION_SAVED',len(R['saved']),flush=True)
