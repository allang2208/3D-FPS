"""Skin actual UE final component poses in the measured camera frame (75 vFOV).
The mesh is the unchanged current V9 export, not a hand-authored arm surrogate.
Morph displacement is not applied to this offline LBS surface measurement.
"""
from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial.transform import Rotation as R
P=Path(__file__).resolve().parent
folder=P/(sys.argv[1] if len(sys.argv)>1 else 'Before')
d=json.loads((folder/'frames-120.json').read_text(encoding='utf-8-sig'))
mesh=json.loads((P.parents[1]/'WarhammerQuickReference20261107/Review/current-mesh.json').read_text())
frames=d['frames'];names=list(frames[0]['bones']);ix={n:i for i,n in enumerate(names)}
def matrix(row):
 m=np.eye(4);m[:3,:3]=R.from_quat(np.roll(row['q'],-1)).as_matrix()*np.array(row['s'])[None,:];m[:3,3]=row['p'];return m
pose=np.array([[matrix(f['bones'][n]) for n in names] for f in frames])
ref=np.array([matrix(mesh['bones'][n]) for n in names]);camera=np.array([matrix(f['mesh_to_camera']) for f in frames])
canonical=np.eye(4);canonical[:3,:3]=np.array([[0,1,0],[1,0,0],[0,0,1]])*.01
world=canonical@camera[:,None]@pose
v=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
weights=np.zeros((len(v),len(names)))
for i,ws in enumerate(mesh['weights']):
 for n,w in ws.items():weights[i,ix[n]]=w
skin=np.zeros((len(frames),len(v),3),np.float32)
for b in range(len(names)):
 use=weights[:,b]>0
 if use.any():skin[:,use]+=np.einsum('fij,vj->fvi',world[:,b]@np.linalg.inv(ref[b]),v[use])[...,:3]*weights[use,b][None,:,None]
tri=np.array(mesh['triangles'],int);dominant=weights.argmax(1)
# The source skeletal package also contains a hidden weapon section. Runtime
# hides that section and attaches its steel hammer separately; omit it from arms.
arm_vertices=weights[:,ix['wpn_root']]<.5
tri=tri[arm_vertices[tri].all(1)]
def unit(v):return v/np.maximum(1e-10,np.linalg.norm(v,axis=-1,keepdims=True))
def angle(a,b):return np.rad2deg(np.arccos(np.clip((unit(a)*unit(b)).sum(-1),-1,1)))
def rotation(m):return R.from_matrix(m[:,:3,:3]/np.linalg.norm(m[:,:3,:3],axis=1,keepdims=True))
def peak(x,minimum=False):
 i=int(np.argmin(x) if minimum else np.argmax(x));return {'value':float(x[i]),'frame':i,'time':frames[i]['time'],'age':frames[i]['age']}
vf=np.tan(np.radians(37.5));hf=vf*16/9
visible=(skin[:,:,1]>.01)&(abs(skin[:,:,0])<skin[:,:,1]*hf)&(abs(skin[:,:,2])<skin[:,:,1]*vf)
report={'native_final_poses':folder.name!='Draft','morph_displacement_in_surface_metrics':False,'frames':len(frames),'sides':{}}
pos=lambda n:pose[:,ix[n],:3,3]
for s in ('l','r'):
 u,l,h=[pos(n+'_'+s) for n in ['upperarm','lowerarm','hand']];upper=l-u;fore=h-l
 hand=rotation(pose[:,ix['hand_'+s]]);bind=rotation(ref[ix['hand_'+s]][None])[0]
 neutral=(hand*bind.inv()).apply(np.broadcast_to(unit(ref[ix['hand_'+s],:3,3]-ref[ix['lowerarm_'+s],:3,3]),fore.shape).copy())
 bend=angle(neutral,fore)
 # Ref-space selection prevents current motion from redefining the shoulder opening.
 root=np.linalg.norm(v[:,:3]-ref[ix['upperarm_'+s],:3,3],axis=1)<8.5
 root&=np.isin(dominant,[ix[n+'_'+s] for n in ['clavicle','upperarm','upperarm_twist_01','upperarm_twist_02']])
 wrist_speed=np.linalg.norm(np.diff(world[:,ix['hand_'+s],:3,3],axis=0),axis=1)*100
 rot_steps={}
 for n in ['upperarm','lowerarm','hand']:
  q=rotation(pose[:,ix[n+'_'+s]]);rot_steps[n]=peak(np.r_[0,(q[1:]*q[:-1].inv()).magnitude()*180/np.pi])
 report['sides'][s]={'wrist_bend_bind_deg':peak(bend),'visible_shoulder_vertices':peak((visible&root[None]).sum(1)),
  'visible_shoulder_nearest_cm':peak(np.where(visible&root[None],np.linalg.norm(skin,axis=-1),np.inf).min(1)*100,True),
  'bone_length_range_cm':{n:[float(np.linalg.norm(seg,axis=1).min()),float(np.linalg.norm(seg,axis=1).max())] for n,seg in [('upper',upper),('fore',fore)]},
  'wrist_frame_travel_cm':peak(np.r_[0,wrist_speed]),'frame_rotation_deg':rot_steps}
report['visible_skin_nearest_cm']=peak(np.where(visible&arm_vertices[None],np.linalg.norm(skin,axis=-1),np.inf).min(1)*100,True)
report['max_surface_frame_travel_cm']=peak(np.r_[0,np.linalg.norm(np.diff(skin,axis=0),axis=-1).max(1)*100])
report['max_arm_surface_frame_travel_cm']=peak(np.r_[0,np.linalg.norm(np.diff(skin[:,arm_vertices],axis=0),axis=-1).max(1)*100])
eye_world=np.array([matrix(f['camera']) for f in frames])
head=np.einsum('fij,j->fi',eye_world@camera@pose[:,ix['wpn_root']],np.array([.150894263,.002343908,.972475657,1.]))[:,:3]
impact=np.array([f['impact'] for f in frames]);landed=np.array([f['landed'] for f in frames]);ages=np.array([f['age'] for f in frames])
contacts=np.flatnonzero(landed)
if len(contacts):
 c=int(contacts[0]);report['landing']={'frame':c,'age':float(ages[c]),'world_time':frames[c]['time'],
  'hammer_marker_error_cm':float(np.linalg.norm(head[c]-impact[c])),
  'head_height_cm':float(head[c,2]),'floor_height_cm':float(impact[c,2]),
  'camera_feedback_degrees':frames[c]['camera_feedback_degrees'],'camera_feedback_cm':frames[c]['camera_feedback_cm']}
 window=(ages>=1.25)&(ages<=1.39)
 report['landing']['planted_marker_error_cm']=float(np.linalg.norm(head[window]-impact[window],axis=1).max())
report['stage_boundaries']=[{'frame':i,'age':float(ages[i]),'from':frames[i-1]['clip'],'to':frames[i]['clip'],
 'surface_travel_cm':float(np.linalg.norm(skin[i]-skin[i-1],axis=-1).max()*100)} for i in range(1,len(frames)) if frames[i]['clip']!=frames[i-1]['clip']]
np.savez_compressed(folder/'evaluated.npz',vertices=skin,mats=world,triangles=tri,names=names,
 time=[f['time'] for f in frames],age=[f['age'] for f in frames],camera=[matrix(f['camera']) for f in frames])
(folder/'surface-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
