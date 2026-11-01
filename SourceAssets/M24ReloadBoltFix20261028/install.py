"""Save only the eight support-chain tracks in fire/cycle/empty-bolt windows."""
import unreal as u,json,copy,shutil,ast,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
import bisect,math
for name in ('packed','find','track','qlerp','sample'):
 exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
patch=json.loads((O/'root_patch.json').read_text());snapshot=json.loads((O/'ue_before.json').read_text())
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
if any(p.get_name() in paths.values() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved M24 profile retained')
live={f:u.load_asset(p) for f,p in paths.items()};before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
receipt={'complete':False,'saved':[],'scope':'left shoulder/elbow clearance; firearm, wrist contacts and fingers retained','reload_fingers_preserved':True,'native_build_required':False}
for key,replacement in patch.items():
 family,role=key.split('/');dst=find(spec[family]['clips'],replacement['base']);expected=find(snapshot['profiles'][family],replacement['base'])
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role];start=(shift+2)/30;end=(shift+55)/30
 for new in replacement['tracks']:
  name=new['bone'];current=next((t for t in dst['tracks'] if t['bone']==name),None);original=next((t for t in expected['tracks'] if t['bone']==name),None)
  if current!=original:raise RuntimeError('Concurrent M24 support change retained '+key+'/'+name)
  if current is None:
   current={'bone':name,'times':[0.,dst['duration']],'values':[0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]*2};dst['tracks'].append(current)
  old=copy.deepcopy(current)
  times=list(old['times'])
  for t in new['times']:
   if start<t<end and all(abs(t-x)>1e-6 for x in times):times.append(t)
  times.sort();values=[];last=None
  for t in times:
   v=sample(new if start+1e-6<t<end-1e-6 else old,t,10,'values')
   if last and sum(a*b for a,b in zip(last,v[3:7]))<0:v[3:7]=[-q for q in v[3:7]]
   last=v[3:7];values.extend(v)
  track(dst,name).update(times=times,values=values)
import runpy
runpy.run_path(str(O/'install_morphs.py'),run_name='__main__')
backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,p in live.items():
 src=Path(u.Paths.project_content_dir())/(paths[family].removeprefix('/Game/')+'.uasset');dest=backup/src.name
 if not dest.exists():shutil.copy2(src,dest)
 (backup/(src.stem+'.json')).write_text(json.dumps(before[family]))
 # The production editor importer is the writer for these read-only structs.
 # Refuse to discard a retained authored clip if a later author adds one.
 if any(c.get_editor_property('retained') is not None for c in p.get_editor_property('clips')):raise RuntimeError('Retained clip requires a different merge path')
 if str(p.get_editor_property('family'))!=family:raise RuntimeError('Unexpected profile family')
 if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Profile import failed '+family)
 if not u.EditorAssetLibrary.save_loaded_asset(p,False):raise RuntimeError('Save failed '+paths[family])
 (O/(family+'_profile.json')).write_text(json.dumps(packed(p,family)))
 receipt['saved'].append({'path':p.get_path_name(),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
 (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('M24_BOLT_ROOT_SAVED',json.dumps(receipt),flush=True)
