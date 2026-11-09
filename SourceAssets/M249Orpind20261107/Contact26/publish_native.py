"""Apply contact corrections directly over the saved delta tracks.

The local correction is derived from UE's actual evaluated pose at its source
time. This avoids resampling the compressed base animation onto another clock.
"""
from pathlib import Path
import json,gzip,pickle,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parent;d=pickle.load(open(r/'current.pkl','rb'));names=d['names'];parents=d['parents'];stats={}
moving=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand'))]
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
for family in ['base','vertical','canted','prism','angled']:
 baseline=r/(family+'.before_native.json.gz')
 if not baseline.exists():baseline.write_bytes((r/(family+'.json.gz')).read_bytes())
 payload=json.load(gzip.open(baseline,'rt'));native=pickle.load(open(r/(family+'_native.pkl'),'rb'))
 for clip in payload['clips']:
  path=clip['base']+'.'+clip['base'].split('/')[-1]
  if path not in native:continue
  rows=native[path];end=3.14 if '_empty' in path else 3.5;times=np.array([2.76]+[row['time'] for row in rows]+[end]);tr=np.zeros((len(times),len(names),3));rv=tr.copy()
  for k,row in enumerate(rows,1):
   old=row['before_world'];new=row['after_world']
   for i in moving:
    a=np.linalg.inv(old[parents[i]])@old[i];b=np.linalg.inv(new[parents[i]])@new[i];v=(R.from_matrix(rot(b))*R.from_matrix(rot(a)).inv()).as_rotvec();p=b[:3,3]-a[:3,3]
    rv[k,i]=v if np.linalg.norm(v)>1e-5 else 0;tr[k,i]=p if np.linalg.norm(p)>1e-5 else 0
  for track in clip['tracks']:
   i=names.index(track['bone'])
   if i not in moving or (not rv[:,i].any() and not tr[:,i].any()):continue
   oldtimes=np.array(track['times']);old=np.array(track['values']).reshape(-1,10);alltimes=np.unique(np.r_[oldtimes,times]);values=np.zeros((len(alltimes),10))
   for j in [0,1,2,7,8,9]:values[:,j]=np.interp(alltimes,oldtimes,old[:,j])
   q=Slerp(oldtimes,R.from_quat(old[:,3:7]))(np.clip(alltimes,oldtimes[0],oldtimes[-1]));inside=(alltimes>=times[0])&(alltimes<=times[-1]);addition=np.zeros((len(alltimes),3));addition[inside]=PchipInterpolator(times,rv[:,i],axis=0)(alltimes[inside]);q=R.from_rotvec(addition)*q;values[:,3:7]=q.as_quat();values[inside,:3]+=PchipInterpolator(times,tr[:,i],axis=0)(alltimes[inside])
   for k in range(1,len(values)):
    if values[k-1,3:7]@values[k,3:7]<0:values[k,3:7]*=-1
   track['times']=alltimes.tolist();track['values']=values.ravel().tolist()
  stats[family+'/'+path.split('.')[-1]]=dict(actual_source_keys=len(rows),before_cm=max(row['before']['max_depth_cm'] for row in rows),after_cm=max(row['after']['max_depth_cm'] for row in rows),additional_wrist_translation_cm=max(np.linalg.norm(row['after_world'][names.index('hand_l'),:3,3]-row['before_world'][names.index('hand_l'),:3,3]) for row in rows),maximum_added_palm_rotation_deg=max(row['after']['rotation_deg'] for row in rows))
  if all('accepted_hand_position' in row for row in rows):
   stats[family+'/'+path.split('.')[-1]]['wrist_offset_from_accepted_cm']=max(float(np.linalg.norm(row['after_world'][names.index('hand_l'),:3,3]-row['accepted_hand_position'])) for row in rows)
 with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(payload,f,separators=(',',':'))
(r/'native_authoring.json').write_text(json.dumps(stats,indent=2));print('CONTACT26_NATIVE_AUTHORED',len(stats),flush=True)
