"""Requested dense source inspection: actual skin, reach, contact and untouched tracks."""
import json,math
from pathlib import Path
import numpy as np
O=Path(__file__).parent;d=json.loads((O/'inputs.json').read_text());old=d['poses'];new=json.loads((O/'candidate_poses.json').read_text());rest={n:np.array(v) for n,v in d['rest'].items()}
skin=d['skin'];names={n for w in skin['weights'] for n in w if n in rest};vv=np.c_[skin['vertices'],np.ones(len(skin['vertices']))]
totals=np.array([sum(w.get(n,0) for n in names) for w in skin['weights']]);group={}
for n in names:
 ids=np.array([i for i,w in enumerate(skin['weights']) if w.get(n,0)>0]);weights=np.array([skin['weights'][i][n]/totals[i] for i in ids])
 group[n]=(ids,vv[ids]@np.linalg.inv(rest[n]).T,weights)
arm_ids=np.array([i for i,w in enumerate(skin['weights']) if sum(v for n,v in w.items() if n.endswith('_r') and n.startswith(('upperarm','lowerarm','clavicle')))/max(totals[i],1e-8)>.85])
camera=np.array([0,-.10,.05]);report={};keyframes={}
def vertices(p):
 out=np.zeros((len(vv),3))
 for n,(ids,loc,w) in group.items():out[ids]+=(loc@np.array(p[n]).T)[:,:3]*w[:,None]
 return out
for label,poses in [('before',old),('after',new)]:
 nearest=(1000,-1);near=[]
 for f in range(248,453):
  v=vertices(poses[f])[arm_ids];distance=float(np.linalg.norm(v-camera,axis=1).min())
  if distance<nearest[0]:nearest=(distance,f)
  if distance<.06:near.append(f)
 report[label]={'minimum_right_arm_camera_distance_mm':nearest[0]*1000,'closest_frame':nearest[1],'frames_within_60mm':near}
bone_errors=[];unchanged=[];held=[]
for f,(before,after) in enumerate(zip(old,new)):
 p={n:np.array(m) for n,m in after.items()};b={n:np.array(m) for n,m in before.items()}
 for a,c in [('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')]:bone_errors.append(abs(np.linalg.norm(p[a][:3,3]-p[c][:3,3])-np.linalg.norm(b[a][:3,3]-b[c][:3,3])))
 unchanged.extend(float(np.max(np.abs(p[n]-b[n]))) for n in p if n.startswith('WPN_') or n.endswith('_l'))
 if 310<=f<=344:held.append(np.linalg.inv(p['WPN_bolt'])@p['hand_r'])
report['max_segment_length_delta_mm']=max(bone_errors)*1000
report['max_weapon_and_left_pose_matrix_delta']=max(unchanged)
report['max_held_hand_translation_delta_mm']=max(np.linalg.norm(m[:3,3]-held[0][:3,3]) for m in held)*1000
report['evidence']='Dense offline actual-skin and source-pose inspection; not a game run. Camera follows the stationary action anchor at vertical FOV 75.'
(O/'source_inspection.json').write_text(json.dumps(report,indent=2));print('SVD_GRASP_SOURCE_INSPECTION',json.dumps(report),flush=True)
