"""Publish only anatomical M24 thumb opposition curves."""
import unreal as u,json,copy,shutil,bisect,math
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/ThumbAnatomy20261028';ACTIVE='/Game/Weapons/M24/MotionPolish20261027'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
patch=json.loads((O/'rotation_patch.json').read_text());snapshot=json.loads((O/'ue_before.json').read_text())
NAMES={'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}
R={'complete':False,'saved':[],'clips':{},'runtime_tested':False,'native_build_required':False,'scope':'three right thumb joint rotation channels only'}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing '+p)
 return a
def packed(p,family):
 return {'family':family,'clips':[{'base':c.get_editor_property('base').get_path_name(),'duration':c.get_editor_property('duration'),'tracks':[
 {'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]} for c in p.get_editor_property('clips')]}
def find(cs,path):return next(c for c in cs if c['base']==path)
def track(c,n):return next(t for t in c['tracks'] if t['bone']==n)
def qlerp(a,b,w):
 dot=sum(x*y for x,y in zip(a,b))
 if dot<0:b=[-x for x in b];dot=-dot
 if dot>.9995:q=[x+(y-x)*w for x,y in zip(a,b)]
 else:
  angle=math.acos(max(-1,min(1,dot)));sn=math.sin(angle)
  q=[(x*math.sin((1-w)*angle)+y*math.sin(w*angle))/sn for x,y in zip(a,b)]
 norm=math.sqrt(sum(x*x for x in q));return [x/norm for x in q]
def sample(t,time,stride,key,quats=False):
 ts=t['times'];vs=t[key];j=bisect.bisect_left(ts,time)
 if j<len(ts) and abs(ts[j]-time)<1e-9:return vs[stride*j:stride*(j+1)]
 i=max(0,min(len(ts)-2,bisect.bisect_right(ts,time)-1))
 a=vs[stride*i:stride*(i+1)]
 if len(ts)==1:return a
 b=vs[stride*(i+1):stride*(i+2)];w=max(0,min(1,(time-ts[i])/(ts[i+1]-ts[i])))
 if quats:return qlerp(a,b,w)
 v=[x+(y-x)*w for x,y in zip(a,b)];v[3:7]=qlerp(a[3:7],b[3:7],w);return v
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 R['saved'].append(a.get_path_name());record()
def create(name):
 p=D+'/'+name
 if E.does_asset_exist(p):return load(p)
 factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
 return A.create_asset(name,D,u.WeaponGripProfile,factory)

targets=[ACTIVE+'/'+n for n in NAMES.values()]
if any(p.get_name() in targets for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
 raise RuntimeError('An active M24 profile has unsaved edits; retained it without publication')
live={f:load(ACTIVE+'/'+n) for f,n in NAMES.items()};before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
for role,data in patch.items():
 families=['mag10'] if role.endswith('_mag10') else (['base'] if role=='reload_empty' else ['base','mag10'])
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role];start=(shift+2)/30;end=(shift+55)/30
 for family in families:
  dst=find(spec[family]['clips'],data['base']);last_saved=O/(family+'_profile.json')
  expected=find(json.loads(last_saved.read_text())['clips'] if last_saved.exists() else snapshot['profiles'][family],data['base'])
  for replacement in data['rotations']:
   n=replacement['bone'];old=copy.deepcopy(track(dst,n))
   if old!=track(expected,n):raise RuntimeError('Concurrent right finger change retained: '+family+'/'+role+'/'+n)
   times=list(old['times'])
   for time in replacement['times']:
    if start<time<end and all(abs(time-t)>1e-6 for t in times):times.append(time)
   times.sort();values=[];last=None
   for time in times:
    v=sample(old,time,10,'values')
    if start+1e-6<time<end-1e-6:v[3:7]=sample(replacement,time,4,'quaternions',True)
    if last is not None and sum(x*y for x,y in zip(last,v[3:7]))<0:v[3:7]=[-x for x in v[3:7]]
    last=v[3:7];values.extend(v)
   target=track(dst,n);target['times']=times;target['values']=values
  R['clips'][family+'/'+role]={'base':data['base'],'bones':[r['bone'] for r in data['rotations']],'preserved_translation_scale':True}
backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,name in NAMES.items():
 path=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset');dest=backup/(name+'.uasset')
 if not dest.exists():shutil.copy2(path,dest)
 json_backup=backup/(name+'.json')
 if not json_backup.exists():json_backup.write_text(json.dumps(before[family]))
for family,name in NAMES.items():
 candidate=create(name)
 if not candidate.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Candidate update failed '+name)
 save(candidate)
for family,name in NAMES.items():
 if not live[family].set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Active update failed '+name)
 save(live[family]);(O/(family+'_profile.json')).write_text(json.dumps(packed(live[family],family)))
R['complete']=True;record();print('M24_THUMB_SAVED',len(R['saved']),flush=True)
