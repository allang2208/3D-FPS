"""Generate scoped profile rows; publishing is handled by install.py."""
from pathlib import Path
import sys,pickle,numpy as np,json,gzip,importlib.util
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('m249_contact_motion',r/'motion.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data=pickle.load(open(r/'corrected.pkl','rb'));returns=pickle.load(open(r/'return_fit.pkl','rb'));profiles={f:[] for f in m.d['profiles']};report={};result={}
post=pickle.load(open(r/'post_world.pkl','rb')) if (r/'post_world.pkl').exists() else {}
settle_spec=importlib.util.spec_from_file_location('contact_settle',r/'settle_motion.py');settle=importlib.util.module_from_spec(settle_spec);settle_spec.loader.exec_module(settle)
left_names={m.names[i] for i in m.left_ids}
for (family,path),row in data.items():
 times=row['times'];w=row['world'].copy();old=row['old'];raw=np.array(m.d['clips'][path]['frames'])
 if (family,path) in returns:
  fitted=returns[(family,path)];curve=PchipInterpolator(fitted['times'],fitted['values'],axis=0)
  for k,tm in enumerate(times):
   if fitted['times'][0]<tm<fitted['times'][-1]:w[k]=m.correct(w[k],curve(tm))
 if (family,path) in post:
  replacement=post[(family,path)];newtimes=replacement['times'];w=replacement['world'].copy()
  old=m.world(settle.interpolate(times,m.encode(old),newtimes))
  raw=settle.interpolate(times,raw,newtimes);times=newtimes
  if '/SideMagazine' in path:w=settle.match_arm_lengths(w,old)
 encoded=m.encode(w);original=next(c for c in m.d['profiles'][family]['clips'] if c['base']==path)
 tracks=[q for q in original['tracks'] if q['bone'] not in left_names]
 for i in m.left_ids:
  v=np.zeros((len(times),10));v[:,:3]=encoded[:,i,:3]-raw[:,i,:3];v[:,3:7]=(R.from_quat(encoded[:,i,3:7])*R.from_quat(raw[:,i,3:7]).inv()).as_quat();v[:,7:]=encoded[:,i,7:]-raw[:,i,7:]
  for k in range(1,len(v)):
   if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
  tracks.append(dict(bone=m.names[i],times=times.tolist(),values=v.ravel().tolist()))
 profiles[family].append(dict(base=path.split('.')[0],duration=m.d['clips'][path]['duration'],tracks=tracks))
 length_error=0.
 for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
  before=np.linalg.norm(old[:,m.ix[a],:3,3]-old[:,m.ix[b],:3,3],axis=1);after=np.linalg.norm(w[:,m.ix[a],:3,3]-w[:,m.ix[b],:3,3],axis=1);length_error=max(length_error,float(np.max(abs(before-after))))
 outside=[i for i,n in enumerate(m.names) if i not in m.left_ids]
 report[family+'/'+path.split('/')[-1]]=dict(arm_length_error_cm=length_error,outside_left_world_change=float(np.max(abs(w[:,outside]-old[:,outside]))),frame_count=len(w))
 if '/SideMagazine' in path:
  finish=3.14 if path.split('.')[0].endswith('_empty') else 3.5;mask=(times>=2.76)&(times<=finish+.01);ids=np.flatnonzero(mask)
  previous=np.array([(np.linalg.inv(m.rigid(fr[m.ix['WPN_root']]))@fr[m.ix['hand_l']])[:3,3] for fr in old[mask]])
  current=np.array([(np.linalg.inv(m.rigid(fr[m.ix['WPN_root']]))@fr[m.ix['hand_l']])[:3,3] for fr in w[mask]])
  acceleration=np.linalg.norm(np.diff(current-previous,n=2,axis=0),axis=1);peak=int(np.argmax(acceleration));stats=report[family+'/'+path.split('/')[-1]]
  stats.update(wrist_path_before_cm=float(np.linalg.norm(np.diff(previous,axis=0),axis=1).sum()),wrist_path_after_cm=float(np.linalg.norm(np.diff(current,axis=0),axis=1).sum()),correction_acceleration_cm=float(acceleration[peak]))
  if acceleration[peak]>2.5:
   (r/'stability_failure.json').write_text(json.dumps(dict(family=family,path=path,source=float(times[ids[peak+1]]),**stats),indent=2));raise RuntimeError('Wrist clearance impulse requires smoothing: '+family+' '+path)
 result[(path,family)]=dict(world=w,times=times)
for family,clips in profiles.items():
 with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
pickle.dump(result,open(r/'candidate_world.pkl','wb'));(r/'authoring.json').write_text(json.dumps(report,indent=2));print('CONTACT25_AUTHORED',sum(len(c) for c in profiles.values()),'profile clips',flush=True)
