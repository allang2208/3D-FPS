"""Read-only deformation diagnosis of the reported traversal and body pose."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def matrix(t):
 m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def posed(d,pose):
 p=np.array(d['positions']);out=np.zeros_like(p);groups={}
 for i,w in enumerate(d['weights']):
  for n,v in w.items():groups.setdefault(n,[]).append((i,v))
 for n,rows in groups.items():
  ids=np.array([i for i,v in rows]);w=np.array([v for i,v in rows]);m=matrix(pose[n])@np.linalg.inv(matrix(d['rest'][n]));out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w[:,None]
 return out
report={}
for profile in ['Traversal','Body']:
 d=read(R/'Before'/profile/'shirt.json');p=np.array(d['positions']);f=np.array(d['triangles']);edges=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);rest=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
 if profile=='Traversal':poses={k:v['bones'] for k,v in read(R/'Before/Traversal/poses.json').items()}
 else:poses={'Current':next(c['bones'] for c in read(R/'live.json')['components'] if c['name']=='CharacterMesh0')}
 rows={}
 for name,pose in poses.items():
  q=posed(d,pose);length=np.linalg.norm(q[edges[:,0]]-q[edges[:,1]],axis=1);i=int(np.argmax(length));rows[name]=dict(max_edge_cm=float(length[i]),stretch=float(length[i]/rest[i]),edge=edges[i].tolist(),rest_position=p[edges[i]].mean(0).tolist(),weights=[d['weights'][v] for v in edges[i]])
 report[profile]=dict(max_rest_edge_cm=float(rest.max()),worst=sorted(rows.items(),key=lambda x:-x[1]['max_edge_cm'])[:3]);print(profile,report[profile])
(R/'diagnosis.json').write_text(json.dumps(report,indent=2))
