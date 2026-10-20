"""User-authorized elbow avoidance; preserve palm targets, finger shape and clocks."""
import json,gzip,copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
from scipy.spatial import ConvexHull
O=Path(__file__).parent;P=O.parents[2]
env={'__file__':str(O/'author_bolt_fit.py')}
exec(compile((O/'author_bolt_fit.py').read_text().split("c=motion['clips']['reload_empty']")[0],'contact_inputs','exec'),env)
motion,rest,ids,parents,matrices,old_pose,ease=[env[k] for k in ('motion','rest','ids','parents','matrices','old_pose','ease')]
names=motion['names'];profile=json.loads((O/'profile_bolt_fit.json').read_text());c=motion['clips']['reload_empty'];clip=next(x for x in profile['clips'] if x['base']==c['path'])
source_profile=json.loads((O.parent/'profile_replacement.json').read_text());source_clip=next(x for x in source_profile['clips'] if x['base']==c['path'])
with gzip.open(P/'SourceAssets/SVCHRefinement20261018/R9ReloadGrip/Inputs/arms.json.gz','rt') as f:a=json.load(f)
vertices=np.asarray(a['positions']);inv=np.linalg.inv(matrices(np.asarray(a['reference'])));weights=np.zeros((len(vertices),len(ids)))
for i,row in enumerate(a['weights']):
 for b,w in row:weights[i,ids[a['weight_bones'][b]]]=w
dom=weights.argmax(1);fore=np.flatnonzero([names[i].startswith('lowerarm') and names[i].endswith('_r') for i in dom])[::5]
hand_ids=np.flatnonzero([names[i].startswith(('hand_','thumb','index','middle','ring','pinky')) and names[i].endswith('_r') for i in dom])[::8]
rear=np.asarray(json.loads((O/'sight_geometry.json').read_text())['SVCH_Detailed_rear']['v'])*[100,-100,100];rear+=np.array([0.,6.5,0.]);center=(rear.min(0)+rear.max(0))*.5;half=(rear.max(0)-rear.min(0))*.5
ci,ui,li,hi,root=[ids[n] for n in ('clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root')]
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def rigid(m):
 out=m.copy();out[:3,:3]/=np.linalg.norm(out[:3,:3],axis=0);return out
def world_at(frame,layer=clip):
 index=int(np.argmin(abs(np.asarray(c['times'])*120-frame)));w=matrices(old_pose(np.asarray(c['frames'][index]),layer,c['times'][index]))
 for i,p in enumerate(parents):
  if p>=0:w[i]=w[p]@w[i]
 return w,index
def swing(a,b):
 a,b=unit(a),unit(b);v=np.cross(a,b);d=np.clip(a@b,-1,1)
 return np.eye(3) if np.linalg.norm(v)<1e-10 else R.from_rotvec(unit(v)*np.arctan2(np.linalg.norm(v),d)).as_matrix()
def aimed(old,oldend,start,end):
 p=old.copy();p[:3,:3]=swing(oldend-old[:3,3],end-start)@old[:3,:3];p[:3,3]=start;return p
def solve(old,angle,target=None,support=None):
 p=old.copy();shoulder,elbow,wrist=[old[j,:3,3] for j in (ui,li,hi)];hand=old[hi].copy()
 if target is not None:
  if np.asarray(target).shape==(4,4):hand=target.copy()
  else:hand[:3,3]=target
 l1,l2=np.linalg.norm(elbow-shoulder),np.linalg.norm(wrist-elbow)
 pole_elbow=elbow
 if support is not None:p[ci]=support[ci];shoulder=support[ui,:3,3];pole_elbow=support[li,:3,3]
 goal=hand[:3,3];axis=unit(goal-shoulder);d=np.linalg.norm(goal-shoulder)
 if d>=l1+l2-.05:raise ValueError('Target beyond fixed arm reach')
 pole=unit(pole_elbow-shoulder-axis*((pole_elbow-shoulder)@axis));pole=R.from_rotvec(axis*np.deg2rad(angle)).apply(pole);along=(l1*l1-l2*l2+d*d)/(2*d);e=shoulder+axis*along+pole*np.sqrt(max(0,l1*l1-along*along))
 du=aimed(old[ui],elbow,shoulder,e)@np.linalg.inv(old[ui]);dl=aimed(old[li],wrist,e,goal)@np.linalg.inv(old[li])
 for i,n in enumerate(names):
  if n.startswith('upperarm') and n.endswith('_r'):p[i]=du@old[i]
  elif n.startswith('lowerarm') and n.endswith('_r'):p[i]=dl@old[i]
 p[hi]=hand
 # Transfer the palm-preserving axial difference through the native forearm helpers.
 fo=R.from_matrix(rigid(old[li])[:3,:3]);fn=R.from_matrix(rigid(p[li])[:3,:3]);ho=R.from_matrix(rigid(old[hi])[:3,:3]);hn=R.from_matrix(rigid(hand)[:3,:3]);q=((fn.inv()*hn)*(fo.inv()*ho).inv()).as_quat()
 if q[3]<0:q=-q
 axis_local=fo.inv().apply(unit(wrist-elbow));roll=2*np.arctan2(q[:3]@axis_local,q[3])
 for name,share in [('lowerarm_twist_01_r',1.),('lowerarm_twist_02_r',.5)]:
  j=ids[name];change=fn*R.from_rotvec(axis_local*roll*share)*fn.inv();p[j,:3,:3]=change.as_matrix()@p[j,:3,:3]
 # Finger component transforms follow the unchanged palm rotation and its target translation.
 dh=hand@np.linalg.inv(old[hi])
 for i,n in enumerate(names):
  if n.startswith(('thumb','index','middle','ring','pinky')) and n.endswith('_r'):p[i]=dh@old[i]
 return p
def skin(w,selected):
 result=np.zeros((len(selected),3))
 for b in np.flatnonzero(weights[selected].max(0)>0):
  m=w[b]@inv[b];result+=(vertices[selected]@m[:3,:3].T+m[:3,3])*weights[selected,b,None]
 m=rest[root]@np.linalg.inv(w[root]);return result@m[:3,:3].T+m[:3,3]
def clearance(w,selected):
 points=skin(w,selected);q=abs(points-center)-half
 surfaces=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(1),0)
 # The native arms have open shoulder ends; ray-based inside signs are unreliable.
 # Check both surface intrusion and containment in a closed local flesh envelope.
 planes=ConvexHull(points).equations
 outside=np.max(rear[::50]@planes[:,:3].T+planes[:,3],axis=1)
 return np.r_[surfaces,outside]

def grip_target(old,angle,frame=None):
 # The contact surface is a cylindrical handle. A rigid roll around its axis
 # preserves each pad's radial and axial distance without bending any finger.
 b=ids['WPN_bolt'];m=old[b]@np.linalg.inv(rest[b]);delta=np.asarray(json.loads((O/'bolt_fit_recipe.json').read_text())['delta_component_cm'])
 center_bind=np.array([2.8268214315,-33.0027878284,-2.7095764875])+delta
 pivot=m[:3,:3]@center_bind+m[:3,3];axis=unit(m[:3,:3]@np.array([1.,0.,0.]));rot=R.from_rotvec(axis*np.deg2rad(angle)).as_matrix();x=np.eye(4);x[:3,:3]=rot;x[:3,3]=pivot-rot@pivot
 hand=x@old[hi]
 if frame is not None:
  approach=float(ease(268,280,frame)*(1-ease(280,304,frame)))
  release=float(ease(344,346,frame)*(1-ease(346,375,frame)))
  g=old[root]@np.linalg.inv(rest[root]);hand[:3,3]+=g[:3,:3]@np.array([6.*approach+3.*release,0.,0.])
 return hand

if __name__=='__main__':
 rows=[]
 for frame in [270,285,300,315,330,345,360,380,400]:
  old,_=world_at(frame);support,_=world_at(frame,source_clip);choices=[]
  for angle in np.arange(-30.,30.1,3.):
   for roll in [0.]:
    target=grip_target(old,float(roll),frame);move=float(np.linalg.norm(target[:3,3]-old[hi,:3,3]))
    if move>(2.5 if 304<=frame<=344 else 4.5):continue
    try:p=solve(old,float(angle),target=target,support=support)
    except ValueError:continue
    dist=np.concatenate([clearance(p,fore),clearance(p,hand_ids)]);pen=float(np.mean(np.maximum(.2-dist,0)**2))+float(np.maximum(.2-dist.min(),0)**2)*.2;choices.append((pen+float(angle*angle)*1e-6+float(roll*roll)*2e-6,float(angle),float(roll),float(dist.min()),move))
  best=min(choices);row={'frame':frame,'best':best,'hand_proxy_min_cm':float(clearance(old,hand_ids).min())};rows.append(row);print(json.dumps(row),flush=True)
 (O/'elbow_scan.json').write_text(json.dumps(rows,indent=2))
