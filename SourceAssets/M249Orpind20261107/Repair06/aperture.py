"""Measure the saved scope aperture against the native component-space eye ray."""
from pathlib import Path
import pickle,json
import numpy as np
import trimesh
from contact_sweep import matrix
r=Path(__file__).resolve().parent
d=pickle.load(open(r/'geometry.pkl','rb'));names=d['names']
pose=matrix(pickle.load(open(r/'idle_local.pkl','rb'))['frames'])[0]
for i,parent in enumerate(d['parents']):
    if parent>=0:pose[i]=pose[parent]@pose[i]
rear=pose[names.index('WPN_RearSight'),:3,3];front=pose[names.index('WPN_FrontSight'),:3,3]
axis=front-rear;axis/=np.linalg.norm(axis);eye=rear-axis*20.
right=np.cross(axis,[0.,0.,1.]);right/=np.linalg.norm(right);up=np.cross(right,axis)
folder=r/'before_idle_ads'
v=np.fromfile(folder/'M249_ads_000.vertices',dtype=np.float32).reshape(-1,3)
faces=np.fromfile(folder/'surface.indices',dtype=np.uint32).reshape(-1,3)
materials=np.fromfile(folder/'surface.materials',dtype=np.uint32)
solid=~np.isin(materials,[7,8,9,16,17]) # Glass and physical red dot intentionally excluded.
model=trimesh.Trimesh(v,faces[solid],process=False)
grid=np.array([(x,y) for x in np.linspace(-1.05,1.05,43) for y in np.linspace(-1.05,1.05,43) if x*x+y*y<=1.05**2])
points=front+grid[:,:1]*right+grid[:,1:]*up
directions=points-eye;directions/=np.linalg.norm(directions,axis=1,keepdims=True)
locations,rays,triangles=model.ray.intersects_location(np.broadcast_to(eye,points.shape),directions,multiple_hits=True)
report={'rays':len(points),'clear_rays':len(points)-len(set(rays)), 'aperture_test_radius_cm':1.05,'blocked_rays':len(set(rays)),'blocker_material_indices':np.unique(materials[solid][triangles]).tolist()}
(r/'aperture_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
