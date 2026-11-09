"""Receiver inertia on the common visual root; preserve every authored joint."""
from pathlib import Path
import sys,pickle,json,gzip,copy,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Insert30'))
import common as c
d=pickle.load(open(r/'current.pkl','rb'));c.d=d;ix=c.ix;names=d['names'];parents=d['parents'];root=ix['root'];parent=parents[root]

# Receiver-space pitch/roll/yaw (degrees) and translation (cm).
# These are broad load/settle beats. Existing short baked contact impulses and
# the single RC1 camera track remain intact and are not amplified or replayed.
shared=[
 (0,(0,0,0),(0,0,0)),(.18,(0,0,0),(0,0,0)),
 (.42,(-.55,-.65,.2),(.12,.04,-.13)),
 (.68,(-1.10,-1.35,.35),(.24,.08,-.24)),
 (.80,(.45,1.35,-.35),(-.16,-.12,.13)),
 (.98,(-.35,-.60,.20),(.08,-.06,-.16)),
 (1.22,(-1.20,-1.70,.50),(.23,-.14,-.34)),
 (1.48,(-.90,-1.30,.40),(.16,-.05,-.26)),
 (1.90,(.30,.55,-.20),(-.08,.10,.10)),
 (2.25,(.10,.40,-.10),(-.05,.08,.02)),
 (2.43,(-.40,-.65,.20),(.13,-.06,-.12)),
 (2.55,(-1.05,-1.70,.40),(.24,-.18,-.20)),
 (2.63,(.30,.45,-.15),(-.08,.04,.10)),
 (2.70,(-.70,-1.25,.20),(.20,-.20,-.17)),
 (2.76,(-1.15,-1.75,.25),(.26,-.27,-.24)),
 (2.91,(.35,.60,-.16),(-.10,.04,.12)),
 (3.02,(-.20,-.30,.08),(.04,-.03,-.05)),
]
normal_tail=[(3.25,(-.15,.15,-.06),(-.03,0,-.03)),(3.50,(0,0,0),(0,0,0)),(3.80,(0,0,0),(0,0,0))]
empty_tail=[
 (3.10,(.20,.20,-.06),(0,.08,.04)),
 (3.18,(.45,.30,-.10),(.03,.12,.06)),
 (3.35,(1.10,.60,.15),(.08,-.38,-.14)),
 (3.41,(1.85,.80,.25),(.12,-.68,-.24)),
 (3.53,(1.55,.60,.18),(.08,-.53,-.18)),
 (3.74,(-.30,-.20,.05),(-.03,.12,.04)),
 (3.87,(-1.10,-.45,.15),(-.07,.36,.15)),
 (4.05,(.30,.15,-.04),(.02,-.06,-.03)),
 (4.28,(0,0,0),(0,0,0)),
 (4.45,(-.20,.12,-.04),(.01,.02,-.04)),
 (4.70,(0,0,0),(0,0,0)),(5.,(0,0,0),(0,0,0)),
]
def motion(t,empty):
 keys=shared+(empty_tail if empty else normal_tail);clock=np.array([v[0]for v in keys]);angles=PchipInterpolator(clock,np.array([v[1]for v in keys]),axis=0)(t);shift=PchipInterpolator(clock,np.array([v[2]for v in keys]),axis=0)(t)
 return angles,shift
def descends(i):
 while i>=0:
  if i==root:return True
  i=parents[i]
 return False
affected=np.array([descends(i)for i in range(len(names))]);assert all(affected[ix[n]]for n in ['WPN_root','hand_l','hand_r','clavicle_l','clavicle_r','ik_hand_root'])
report={};candidates={}
for family,p in d['profiles'].items():
 clips=[]
 for path,clip in d['clips'].items():
  if '/SideMagazine'not in path:continue
  t=np.array(clip['times']);raw=np.array(clip['frames']);oldlocal=c.layer(raw,path,family,t);before=c.world(oldlocal);empty=path.endswith('_empty');angles,shift=motion(t,empty)
  # A receiver-relative rear grip pivot keeps the supporting hand steady.
  gun=before[:,ix['WPN_root']];grot=gun[:,:3,:3]/np.linalg.norm(gun[:,:3,:3],axis=1)[:,None,:]
  pivot_local=grot[0].T@(before[0,ix['hand_r'],:3,3]-gun[0,:3,3]);pivot=gun[:,:3,3]+np.einsum('kij,j->ki',grot,pivot_local)
  spin=grot@R.from_euler('xyz',angles,degrees=True).as_matrix()@grot.transpose(0,2,1)
  xf=np.tile(np.eye(4),(len(t),1,1));xf[:,:3,:3]=spin;xf[:,:3,3]=pivot+np.einsum('kij,kj->ki',grot,shift)-np.einsum('kij,kj->ki',spin,pivot)
  desired=before.copy();desired[:,affected]=xf[:,None]@before[:,affected]
  local=np.linalg.inv(before[:,parent])@desired[:,root];scale=np.linalg.norm(local[:,:3,:3],axis=1)
  delta=np.zeros((len(t),10));delta[:,:3]=local[:,:3,3]-raw[:,root,:3];delta[:,3:7]=(R.from_matrix(local[:,:3,:3]/scale[:,None,:])*R.from_quat(raw[:,root,3:7]).inv()).as_quat();delta[:,7:]=oldlocal[:,root,7:]-raw[:,root,7:]
  old=next(q for q in p['clips']if q['base']==path);incoming=copy.deepcopy(old);incoming.pop('retained',None)
  assert not old.get('retained')
  # Every non-root track is copied verbatim, including Insert30 arm corrections.
  incoming['tracks']=[q for q in incoming['tracks']if q['bone']!='root']
  for k in range(1,len(delta)):
   if delta[k-1,3:7]@delta[k,3:7]<0:delta[k,3:7]*=-1
  incoming['tracks'].append(dict(bone='root',times=np.asarray(t,np.float32).astype(float).tolist(),values=delta.ravel().tolist()));clips.append(incoming)
  check=oldlocal.copy();check[:,root,:3]=raw[:,root,:3]+delta[:,:3];check[:,root,3:7]=(R.from_quat(delta[:,3:7])*R.from_quat(raw[:,root,3:7])).as_quat();after=c.world(check)
  expected_error=float(np.abs(after-desired).max());relative_error=float(np.abs(np.linalg.inv(after[:,ix['WPN_root']])@after[:,ix['hand_l']]-np.linalg.inv(before[:,ix['WPN_root']])@before[:,ix['hand_l']]).max())
  end=4.7 if empty else 3.5;zero=(t<=.18)|(t>=end);zero_error=float(np.abs(after[zero]-before[zero]).max())
  report[family+'/'+path.split('.')[-1]]=dict(changed_tracks=['root'],root_motion=clip['root_motion'],rigid_transform_error=expected_error,grip_relative_error=relative_error,entry_exit_error=zero_error,max_added_angle_deg=float(np.degrees(R.from_matrix(spin).magnitude()).max()),max_added_translation_cm=float(np.linalg.norm(shift,axis=1).max()),duration=clip['duration'])
  candidates[(path,family)]=dict(times=t,before=before,after=after,delta=xf)
  print('FEEDBACK31_AUTHORED',family,path.split('.')[-1],expected_error,relative_error,flush=True)
 with gzip.open(r/(family+'.json.gz'),'wt')as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
assert len(report)==10 and all(v['rigid_transform_error']<1e-3 and v['grip_relative_error']<1e-5 and v['entry_exit_error']<1e-3 for v in report.values())
(r/'authoring.json').write_text(json.dumps(report,indent=2));pickle.dump(candidates,open(r/'candidate.pkl','wb'))
