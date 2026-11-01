"""Merge only reload left-finger rotations into the live M24 profiles."""
import unreal as u,json,copy,shutil,bisect,math
from pathlib import Path
O=Path(__file__).resolve().parent;ACTIVE='/Game/Weapons/M24/MotionPolish20261027'
E=u.EditorAssetLibrary
patch=json.loads((O/'rotation_patch.json').read_text());snapshot=json.loads((O/'ue_before.json').read_text())
NAMES={'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}
R={'complete':False,'saved':[],'clips':{},'runtime_tested':False,'scope':'15 left finger rotation channels in four reload variants; source frames 4-54'}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
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
 i=max(0,min(len(ts)-2,bisect.bisect_right(ts,time)-1));a=vs[stride*i:stride*(i+1)]
 if len(ts)==1:return a
 b=vs[stride*(i+1):stride*(i+2)];w=max(0,min(1,(time-ts[i])/(ts[i+1]-ts[i])))
 if quats:return qlerp(a,b,w)
 v=[x+(y-x)*w for x,y in zip(a,b)];v[3:7]=qlerp(a[3:7],b[3:7],w);return v
targets=[ACTIVE+'/'+n for n in NAMES.values()]
if any(p.get_name() in targets for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
 raise RuntimeError('An active M24 profile has unsaved edits; retained it without publication')
live={f:u.load_asset(ACTIVE+'/'+n) for f,n in NAMES.items()}
if any(p is None for p in live.values()):raise RuntimeError('Missing M24 profile')
before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
for role,data in patch.items():
 family='mag10' if role.endswith('_mag10') else 'base';dst=find(spec[family]['clips'],data['base'])
 expected=find(snapshot['profiles'][family],data['base']);start,end=data['window']
 for replacement in data['rotations']:
  n=replacement['bone'];old=copy.deepcopy(track(dst,n))
  if old!=track(expected,n):raise RuntimeError('Concurrent left finger change retained: '+family+'/'+role+'/'+n)
  times=list(old['times'])
  for time in replacement['times']:
   if start<=time<=end and all(abs(time-t)>1e-6 for t in times):times.append(time)
  times.sort();values=[];last=None
  for time in times:
   v=sample(old,time,10,'values')
   if start+1e-6<time<end-1e-6:v[3:7]=sample(replacement,time,4,'quaternions',True)
   if last is not None and sum(x*y for x,y in zip(last,v[3:7]))<0:v[3:7]=[-x for x in v[3:7]]
   last=v[3:7];values.extend(v)
  target=track(dst,n);target['times']=times;target['values']=values
 R['clips'][family+'/'+role]={'base':data['base'],'bones':[r['bone'] for r in data['rotations']]}
backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,name in NAMES.items():
 path=Path(u.Paths.project_content_dir())/'Weapons/M24/MotionPolish20261027'/(name+'.uasset');dest=backup/(name+'.uasset')
 if not dest.exists():shutil.copy2(path,dest)
 json_backup=backup/(name+'.json')
 if not json_backup.exists():json_backup.write_text(json.dumps(before[family]))
for family,name in NAMES.items():
 if not live[family].set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Active update failed '+name)
 if not E.save_loaded_asset(live[family],False):raise RuntimeError('Save failed '+name)
 R['saved'].append(live[family].get_path_name());record()
 (O/(family+'_profile.json')).write_text(json.dumps(packed(live[family],family)))
R['complete']=True;record();print('M24_RELOAD_FINGERS_SAVED',len(R['saved']),flush=True)
