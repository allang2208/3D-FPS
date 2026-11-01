import json,gzip,math
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'Inputs/geometry.json.gz','rt'));donor=json.loads((O/'Inputs/m4_donor.json').read_text())
rows={}
for n in donor['names']:
 v=donor['pose'][n];m=np.eye(4);m[:3,:3]=Rotation.from_quat(v[3:7]).as_matrix()@np.diag(v[7:]);m[:3,3]=v[:3];p=donor['parents'][n];rows[n]=rows[p]@m if p else m
relative={n:(np.linalg.inv(rows['WPN_root'])@m).tolist() for n,m in rows.items()}
data={'m4_hand_root':{n:relative[n] for n in ('hand_r','thumb_03_r','index_03_r','middle_03_r','pinky_03_r')},'m4_donor_root_matrices':relative}
h=D['M24'];v=np.array(h['positions'])*[.01,-.01,.01];f=np.array(h['triangles']);mi=np.array(h['material_ids']);edges={}
for i,tri in enumerate(f):
 if mi[i] not in (4,5):continue
 for a,b in zip(tri,np.roll(tri,-1)):
  key=tuple(sorted((tuple(np.round(v[a],6)),tuple(np.round(v[b],6)))))
  edges.setdefault(key,set()).add(int(mi[i]))
seam=[e for e,m in edges.items() if m=={4,5}];data['actual_front_cut_edges']=seam
data['actual_front_cut_bounds']=[np.array(seam).reshape(-1,3).min(0).tolist(),np.array(seam).reshape(-1,3).max(0).tolist()]
(O/'Inputs/layout.json').write_text(json.dumps(data,indent=2))
print('M4 hand roots', {n:np.array(relative[n])[:3,3].tolist() for n in data['m4_hand_root']})
print('Actual M24 front seam',len(seam),data['actual_front_cut_bounds'])
