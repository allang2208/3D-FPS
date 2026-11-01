"""Merge only the continuous reload window into both live M24 profiles."""
import unreal as u,json,copy,ast,hashlib,shutil,bisect,math
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for name in ('packed','find','qlerp','sample'):
 exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; M24 assets not modified')
snapshot=json.loads((O/'ue_before.json').read_text());patch=json.loads((O/'flow_patch.json').read_text())
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths.values()):raise RuntimeError('Unsaved M24 profile retained')
live={f:u.load_asset(p) for f,p in paths.items()};before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
for family,p in live.items():
 if any(c.get_editor_property('retained') is not None for c in p.get_editor_property('clips')):raise RuntimeError('Retained clip requires a separate merge')
for key,replacement in patch.items():
 family,role=key.split('/');dst=find(spec[family]['clips'],replacement['base']);expected=find(snapshot['profiles'][family],replacement['base']);start,end=replacement['window']
 for new in replacement['tracks']:
  name=new['bone'];current=next((t for t in dst['tracks'] if t['bone']==name),None);original=next((t for t in expected['tracks'] if t['bone']==name),None)
  if current!=original:raise RuntimeError('Concurrent M24 release change retained '+key+'/'+name)
  if current is None:
   current={'bone':name,'times':[0.,dst['duration']],'values':[0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]*2};dst['tracks'].append(current)
  old=copy.deepcopy(current);times=list(old['times'])
  for t in new['times']:
   if start<=t<=end and all(abs(t-x)>1e-6 for x in times):times.append(t)
  times.sort();values=[];last=None
  for t in times:
   v=sample(new if start+1e-6<t<end-1e-6 else old,t,10,'values')
   if last and sum(a*b for a,b in zip(last,v[3:7]))<0:v[3:7]=[-q for q in v[3:7]]
   last=v[3:7];values.extend(v)
  current.update(times=times,values=values)
backup=O/'Backups';backup.mkdir(exist_ok=True);receipt={'complete':False,'saved':[],'scope':'four reload variants, source 20-50, continuous extraction/toss/retrieval and retreat','runtime_tested':False}
for family,p in live.items():
 disk=Path(u.Paths.project_content_dir())/(paths[family].removeprefix('/Game/')+'.uasset');dest=backup/disk.name
 if not dest.exists():shutil.copy2(disk,dest)
 (backup/(family+'.json')).write_text(json.dumps(before[family]))
 if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Profile import failed '+family)
 if not u.EditorAssetLibrary.save_loaded_asset(p,False):raise RuntimeError('Profile save failed '+family)
 (O/(family+'_profile.json')).write_text(json.dumps(packed(p,family)))
 receipt['saved'].append({'path':p.get_path_name(),'sha256':hashlib.sha256(disk.read_bytes()).hexdigest()})
 (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('M24_FLOW_PROFILES_SAVED',json.dumps(receipt),flush=True)
exec(compile((O/'readback.py').read_text(),'M24_flow_readback','exec'))
