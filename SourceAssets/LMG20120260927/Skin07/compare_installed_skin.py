"""Focused before/after measurement of the installed compressed 201 elbow skin."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
before=json.loads((O/'installed_skin.json').read_text())
after=json.loads((O/'installed_skin_after.json').read_text())
def mat(t):
 m=np.eye(4);m[:3,:3]=np.asarray(t['axes']).T;m[:3,3]=t['position'];return m
def unit(v):return v/np.linalg.norm(v)
def between(a,b):
 a=unit(a);b=unit(b);c=np.cross(a,b);s=np.linalg.norm(c)
 return Rotation.from_rotvec(c/s*np.arctan2(s,np.dot(a,b))).as_matrix() if s>1e-8 else np.eye(3)
def angle(m,axis):
 q=Rotation.from_matrix(m).as_quat();q=q if q[3]>=0 else -q
 return float(np.degrees(2*np.arctan2(np.dot(q[:3],axis),q[3])))
B={n:mat(t) for n,t in before['bones'].items()};V=np.asarray(before['positions']);W=before['weights'];F=np.asarray(before['triangles'])
axis=unit(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);length=np.linalg.norm(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);along=(V-B['lowerarm_l'][:3,3])@axis/length
left=np.array([sum(w for n,w in ws.items() if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand_')))>.98 for ws in W])
cap=left&(along>-.12)&(along<.16);capids=np.where(cap)[0]
fore=['lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
# Follow the same original skin vertices around the elbow rather than treating
# a skinning-matrix determinant as literal anatomical volume.
bands={str(s):np.where(left&(np.abs(along-s)<.0125))[0] for s in (0.,.05,.10,.15)}
def measure(data,key):
 P={n:mat(t) for n,t in data['poses'][key].items()};D={n:P[n]@np.linalg.inv(B[n]) for n in P}
 fa=unit(P['hand_l'][:3,3]-P['lowerarm_l'][:3,3]);up=Rotation.from_matrix(D['upperarm_l'][:3,:3]).as_matrix();zero=between(up@axis,fa)@up
 roll={n:angle(D[n][:3,:3]@zero.T,fa) for n in fore}
 posed=np.zeros_like(V);dets=[]
 for i in np.where(left)[0]:
  g=np.zeros((3,3))
  for n,w in W[i].items():
   if n in D:
    posed[i]+=w*(D[n][:3,:3]@V[i]+D[n][:3,3]);g+=w*D[n][:3,:3]
  if cap[i]:dets.append(np.linalg.det(g))
 sections={}
 for s,ids in bands.items():
  points=posed[ids];center=points.mean(axis=0);offset=points-center
  offset-=np.outer(offset@fa,fa)
  ev=np.maximum(np.linalg.eigvalsh(offset.T@offset/len(ids)),0.)
  sections[s]={'vertices':len(ids),'minor_major_rms_radius_cm':np.sqrt(ev[-2:]).tolist()}
 return {'forearm_roll_degrees':roll,'elbow_blended_rotation_determinant':{'vertices':len(capids),'min':float(min(dets)),'p05_median':np.percentile(dets,[5,50]).tolist()},'posed_skin_band_radii':sections}
out={'source':'UE COMPRESSED animation + installed native skin','not_visual_acceptance':True,'metric_note':'Determinant is a linear blend contraction indicator, not anatomical volume. Band radii are RMS spread of the same actual skinned vertices projected normal to elbow-wrist axis.','mesh_positions_max_difference_cm':float(np.max(np.abs(np.asarray(after['positions'])-V))),'weights_unchanged':before['weights']==after['weights'],'triangles_unchanged':before['triangles']==after['triangles'],'samples':{}}
for key in before['poses']:
 a=measure(before,key);b=measure(after,key)
 p0={n:mat(t) for n,t in before['poses'][key].items()};p1={n:mat(t) for n,t in after['poses'][key].items()}
 maxpos=max(float(np.linalg.norm(p0[n][:3,3]-p1[n][:3,3])) for n in p0)
 contacts=[n for n in p0 if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))]
 maxrot=max(float(np.degrees(Rotation.from_matrix(p1[n][:3,:3]@np.linalg.inv(p0[n][:3,:3])).magnitude())) for n in contacts)
 out['samples'][key]={'before':a,'after':b,'max_bone_position_difference_cm':maxpos,'max_hand_finger_rotation_difference_degrees':maxrot}
 print(key,'roll',b['forearm_roll_degrees'],'elbow',a['elbow_blended_rotation_determinant']['p05_median'],'->',b['elbow_blended_rotation_determinant']['p05_median'],'contact_cm',maxpos,'contact_deg',maxrot,flush=True)
(O/'installed_skin_comparison.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('201_SKIN07_COMPRESSED_SKIN_COMPARED')