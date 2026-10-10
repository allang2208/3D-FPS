"""Measure actual evaluated native bones and glove/shaft surface intersection."""
import json,os
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh

out=Path(os.environ.get('STAFF_DIAG_ROOT','D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffCheck20261009'))
d=json.loads((out/'poses.json').read_text())
report={'scope':d['scope'],'poses':{},'grip_surface':{}}
for row in d['samples']:
 b=row['bones'];hands={}
 for side in ['r','l']:
  s,e,w=[np.array(b[n+'_'+side][:3]) for n in ['upperarm','lowerarm','hand']]
  u=e-s;v=w-e
  bend=np.degrees(np.arccos(np.clip(np.dot(u,v)/np.linalg.norm(u)/np.linalg.norm(v),-1,1)))
  hands[side]={'upper_cm':float(np.linalg.norm(u)),'forearm_cm':float(np.linalg.norm(v)),
   'elbow_flexion_deg':float(bend),'wrist':w.tolist(),'elbow':e.tolist()}
 report['poses'][row['label']]=hands
row=next(x for x in d['samples'] if x['label']=='idle')
v=np.fromfile(out/'staff.vertices',dtype='<f4').reshape(-1,3)
t=np.fromfile(out/'staff.indices',dtype='<u4').reshape(-1,3)
parts=trimesh.Trimesh(v,t,process=True).split(only_watertight=False)
# Use the original closed grip insert, not an open crop of the staff surface.
shaft=next(p for p in parts if p.bounds[0,2]<32<p.bounds[1,2])
shaft.fix_normals()
assert shaft.is_watertight
g=np.fromfile(out/'idle.ue_steel_gauntlets.vertices',dtype='<f4').reshape(-1,3)
hand=np.array(row['bones']['hand_r'][:3]);g=g[np.linalg.norm(g-hand,axis=1)<17]
frame=row['staff'];r=Rotation.from_quat(frame[3:7]).as_matrix()
g=((g-np.array(frame[:3]))@r)/np.array(frame[7:10]);g=np.unique(np.round(g,4),axis=0)
g=g[(np.linalg.norm(g[:,:2],axis=1)<8)&(np.abs(g[:,2]-32)<16)]
# Ray containment establishes the sign; closest-point distance measures depth.
# Do not infer containment from nearest triangle normals at sharp cap edges.
box=np.all((g>shaft.bounds[0])&(g<shaft.bounds[1]),axis=1)
inside=g[box];inside=inside[shaft.contains(inside)]
dist=np.concatenate([trimesh.proximity.closest_point(shaft,inside[i:i+256])[1] for i in range(0,len(inside),256)]) if len(inside) else np.array([0.])
report['grip_surface']={'shaft_watertight':bool(shaft.is_watertight),'grip_bounds_cm':shaft.bounds.tolist(),'right_glove_unique_vertices':len(g),
 'vertices_inside_over_1mm':int(np.sum(dist>.1)),'maximum_penetration_cm':float(max(0,dist.max())),
 'note':'Ray containment plus unsigned nearest-surface distance against the original watertight grip insert. Actual CPU skin vertex samples, not a full triangle-intersection proof. Distances are in staff-local centimeters.'}
(out/'measurements.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'samples':len(d['samples']),'grip':report['grip_surface'],
 'elbow_flexion_range':{side:[min(x[side]['elbow_flexion_deg'] for x in report['poses'].values()),max(x[side]['elbow_flexion_deg'] for x in report['poses'].values())] for side in ['r','l']}},indent=2))
