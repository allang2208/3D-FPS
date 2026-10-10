"""Inspect every authored skin vertex against the original closed grip insert."""
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
import author_staff_surface_repair20261009 as a

row=a.read(a.CHECK/'poses.json')['samples'][0];w=a.staff_fingers(a.from_sample(row))
fit=a.read(a.OUT/'contact-fit.json')['false'];base={n:m.copy() for n,m in w.items()}
for n in a.descendants('hand_r'):
    pn=a.parents[n];lm=np.linalg.inv(base[pn])@base[n]
    if n in fit['finger_delta']:lm[:3,:3]=lm[:3,:3]@a.R.from_quat(fit['finger_delta'][n]).as_matrix()
    elif '_half_' in n and pn in fit['finger_delta']:
        delta=a.local[pn][:3,:3].T@(np.linalg.inv(w[a.parents[pn]])@w[pn])[:3,:3]
        lm[:3,:3]=a.R.from_rotvec(-.5*a.R.from_matrix(delta).as_rotvec()).as_matrix()@a.local[n][:3,:3]
    w[n]=w[pn]@lm
staff=w['hand_r']@np.array(fit['contact_in_hand'])@a.matrix(np.eye(3),[0,0,-32]);inv=np.linalg.inv(staff)
v=np.fromfile(a.CHECK/'staff.vertices',dtype='<f4').reshape(-1,3);tri=np.fromfile(a.CHECK/'staff.indices',dtype='<u4').reshape(-1,3)
m=next(c for c in trimesh.Trimesh(v,tri,process=True).split(only_watertight=False) if c.bounds[0,2]<32<c.bounds[1,2]);m.fix_normals()
report={};critical=a.read(a.OUT/'critical-vertices.json') if (a.OUT/'critical-vertices.json').exists() else {}
for label,g in [('steel',a.read(a.OUT/'steel-repaired.json')),('skin',a.geos['body'])]:
    p=a.skin(g,w);p=p@inv[:3,:3].T+inv[:3,3]
    ids=np.flatnonzero(np.all((p>m.bounds[0])&(p<m.bounds[1]),axis=1));ids=ids[m.contains(p[ids])]
    dist=trimesh.proximity.closest_point(m,p[ids])[1] if len(ids) else np.array([])
    report[label]=dict(inside_vertices=len(ids),over_1mm=int(sum(dist>.1)),maximum_mm=float(max(dist,default=0)*10))
    if len(ids):
        points=np.array(g['positions']);near=cKDTree(points).query(points[ids],k=24)[1].ravel()
        critical[label]=np.union1d(critical.get(label,[]),near).astype(int).tolist()
print(json.dumps(report))
(a.OUT/'critical-vertices.json').write_text(json.dumps(critical))
(a.OUT/'full-contact-check.json').write_text(json.dumps(report,indent=2))
