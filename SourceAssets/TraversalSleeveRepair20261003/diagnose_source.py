"""Quantify the reported defect on the captured original source, not a game test."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def matrix(t):
    m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
d=read(R/'Before/ue_chainmail_shirt.json');v=np.array(d['positions']);f=np.array(d['triangles']);ws=d['weights']
edges=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
rest_length=np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)
groups={}
for i,w in enumerate(ws):
    for name,value in w.items():groups.setdefault(name,[]).append((i,value))
groups={n:(np.array([i for i,_ in rows]),np.array([w for _,w in rows])[:,None],np.linalg.inv(matrix(d['rest'][n]))) for n,rows in groups.items()}
report={'asset':d['source'],'asset_sha256':d['asset_sha256'],'scope':'Original saved source and compressed source clips; no runtime IK, WPO, camera or render acceptance','actions':{}}
for pose in read(R/'source-poses.json'):
    p=np.zeros_like(v)
    for name,(ids,weight,inv) in groups.items():
        m=matrix(pose['bones'][name])@inv;p[ids]+=(v[ids]@m[:3,:3].T+m[:3,3])*weight
    lengths=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1);idx=int(np.argmax(lengths))
    row={'time':pose['time'],'max_edge_cm':float(lengths[idx]),'rest_edge_cm':float(rest_length[idx]),
         'end_weights':[ws[i] for i in edges[idx]],'rest_positions':v[edges[idx]].tolist()}
    old=report['actions'].get(pose['action'])
    if old is None or row['max_edge_cm']>old['max_edge_cm']:report['actions'][pose['action']]=row
torso=np.array([sum(value for name,value in w.items() if name.startswith(('spine','clavicle'))) for w in ws])
report['vertices_with_torso_weight_over_half']=int(sum(torso>.5))
report['maximum_torso_weight']=float(torso.max())
report['lod_policy']=read(R/'Before/ue_chainmail_shirt-lod-policy.json')
(R/'source-diagnosis.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'torso_vertices':report['vertices_with_torso_weight_over_half'],'actions':{k:{x:v[x] for x in ['time','max_edge_cm','rest_edge_cm']} for k,v in report['actions'].items()}},indent=2))
