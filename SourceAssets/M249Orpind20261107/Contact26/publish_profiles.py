"""Publish contact-only deltas over the currently installed compact return."""
from pathlib import Path
import importlib.util,pickle,json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import gaussian_filter1d
r=Path(__file__).resolve().parent;previous=r.parent/'Contact25'
def module(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
m=module('contact26_motion',previous/'motion.py');q=module('contact26_settle',previous/'settle_motion.py')
d=pickle.load(open(r/'current.pkl','rb'));m.d=d;m.s['d']=d
baseline=pickle.load(open(r/'baseline.pkl','rb'));out={};profiles={f:[] for f in d['profiles']};report={}
guarded=pickle.load(open(r/'guarded_world.pkl','rb')) if (r/'guarded_world.pkl').exists() else {}
left_names={m.names[i] for i in m.left_ids}
def weight(w,ref,path,t):
 hand=np.linalg.inv(m.rigid(w[m.ix['WPN_root']]))@w[m.ix['hand_l']]
 distance=np.linalg.norm(hand[:3,3]-ref[:3,3]);angle=np.degrees(np.linalg.norm(R.from_matrix(m.rot(hand)@m.rot(ref).T).as_rotvec()))
 a=(1-m.ease((distance-.5)/3.5))*(1-m.ease((angle-4)/28))
 if path.split('.')[-1]=='A_M249_idle':a=1.
 if '/SideMagazine' in path and t>2.76:
  end=3.14 if '_empty' in path else 3.5;a=m.ease(((t-2.76)/(end-2.76)-.7)/.3)
 return float(a)
for family in profiles:
 state=pickle.load(open(r/(family+'_fit.pkl'),'rb'));idle=state['idle']['parameters'];ref=state['reference_hand']
 for (fam,path),row in baseline.items():
  if fam!=family or (fam=='base' and '/SideMagazine' not in path):continue
  old=row['world'];times=row['times'];new=old.copy();side='/SideMagazine' in path;end=3.14 if '_empty' in path else 3.5
  params=np.zeros((len(times),len(idle)))
  if side:
   curve=state['curves'][path];dense=np.linspace(2.76,end,int(np.ceil((end-2.76)*480))+1)
   values=np.array([np.interp(dense,curve['times'],curve['values'][:,j]) for j in range(len(idle))]).T
   values=gaussian_filter1d(values,.012/(dense[1]-dense[0]),axis=0,mode='nearest')
   values*=np.array(m.ease((dense-2.76)/.025)*m.ease((end-dense)/.025))[:,None]
   params=np.array([np.interp(times,dense,values[:,j],left=0,right=0) for j in range(len(idle))]).T
  for k,t in enumerate(times):
   a=weight(old[k],ref,path,t)
   if a>1e-9:new[k]=m.correct(old[k],idle*a)
   if side and 2.76<t<end:new[k]=m.correct(new[k],params[k])
  if (path,family) in guarded:new=q.match_arm_lengths(guarded[(path,family)]['world'],old)
  raw=q.interpolate(np.array(d['clips'][path]['times']),np.array(d['clips'][path]['frames']),times);encoded=m.encode(new)
  original=next(c for c in d['profiles'][family]['clips'] if c['base']==path)
  tracks=[v for v in original['tracks'] if v['bone'] not in left_names]
  for i in m.left_ids:
   v=np.zeros((len(times),10));v[:,:3]=encoded[:,i,:3]-raw[:,i,:3]
   v[:,3:7]=(R.from_quat(encoded[:,i,3:7])*R.from_quat(raw[:,i,3:7]).inv()).as_quat();v[:,7:]=encoded[:,i,7:]-raw[:,i,7:]
   for k in range(1,len(v)):
    if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
   tracks.append(dict(bone=m.names[i],times=times.tolist(),values=v.ravel().tolist()))
  profiles[family].append(dict(base=path.split('.')[0],duration=d['clips'][path]['duration'],tracks=tracks))
  outside=[i for i in range(len(m.names)) if i not in m.left_ids];hand=m.ix['hand_l'];armerror=0.
  for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
   a,b=m.ix[a],m.ix[b];armerror=max(armerror,float(np.max(abs(np.linalg.norm(new[:,a,:3,3]-new[:,b,:3,3],axis=1)-np.linalg.norm(old[:,a,:3,3]-old[:,b,:3,3],axis=1)))))
  report[family+'/'+path.split('.')[-1]]=dict(wrist_offset_cm=float(np.linalg.norm(new[:,hand,:3,3]-old[:,hand,:3,3],axis=1).max()),wrist_rotation_deg=float(np.degrees(np.linalg.norm((R.from_matrix(np.array([m.rot(v) for v in new[:,hand]]))*R.from_matrix(np.array([m.rot(v) for v in old[:,hand]])).inv()).as_rotvec(),axis=1)).max()),arm_length_error_cm=armerror,outside_left_world_change=float(np.max(abs(new[:,outside]-old[:,outside]))),duration_unchanged=True,return_times_unchanged=True)
  out[(path,family)]=dict(world=new,times=times,parameters=params)
for family,clips in profiles.items():
 with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
pickle.dump(out,open(r/'candidate_world.pkl','wb'));(r/'authoring.json').write_text(json.dumps(report,indent=2))
print('CONTACT26_AUTHORED',sum(len(c) for c in profiles.values()),'profile clips',flush=True)
if not guarded:raise SystemExit(2)
