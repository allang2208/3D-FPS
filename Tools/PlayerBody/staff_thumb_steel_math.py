"""Shared author-space geometry for the scoped thumb and Jason armor repair."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
import trimesh
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffThumbSteel20261009'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def matrix(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
target=read('SourceAssets/JasonPlayer20261003/Jason.json')
names=[b['name'] for b in target['bones']]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in target['bones']}
rest={b['name']:matrix(np.array(b['axes']).T,b['position']) for b in target['bones']}
local={n:np.linalg.inv(rest[parents[n]])@rest[n] if parents[n] else rest[n] for n in names}
def below(n):
    while parents[n]:
        n=parents[n]
        if n=='hand_r':return True
    return False
children=[n for n in names if below(n)]
def pose(g,thumb=None):
    rotations=dict(g['rotations'])
    if thumb:rotations.update(thumb)
    w=dict(rest);w['hand_r']=np.array(g['hand_in_grip'])
    for n in children:
        q=R.from_quat(rotations[n]).as_matrix() if n in rotations else local[n][:3,:3]
        if '_half_' in n and parents[n] in rotations:
            d=local[parents[n]][:3,:3].T@R.from_quat(rotations[parents[n]]).as_matrix()
            q=R.from_rotvec(-R.from_matrix(d).as_rotvec()*.5).as_matrix()@local[n][:3,:3]
        w[n]=w[parents[n]]@matrix(q,local[n][:3,3])
    # Unposed forearm contributors at the hand cut move rigidly with the wrist.
    for n in names:
        if n not in children and n!='hand_r':w[n]=w['hand_r']@np.linalg.inv(rest['hand_r'])@rest[n]
    return w
def skin(geo,w):
    p=np.array(geo['positions']);out=np.zeros_like(p);entries={}
    for i,ws in enumerate(geo['weights']):
        for b,v in ws:entries.setdefault(names[b],[]).append((i,v))
    for n,rows in entries.items():
        rows=np.array(rows);ids=rows[:,0].astype(int);m=w[n]@np.linalg.inv(rest[n])
        out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*rows[:,1,None]
    return out
def nearest_surface(query,p,t):
    centers=p[t].mean(1);tree=cKDTree(centers);result=[];normals=[];closest=[];indices=[]
    for begin in range(0,len(query),1024):
        q=query[begin:begin+1024];_,ix=tree.query(q,k=min(24,len(t)));a=p[t[ix]]
        cp=trimesh.triangles.closest_point(a.reshape(-1,3,3),np.repeat(q,a.shape[1],axis=0)).reshape(a.shape[:2]+(3,))
        best=np.argmin(np.linalg.norm(cp-q[:,None,:],axis=2),axis=1)
        ids=np.arange(len(q));cp=cp[ids,best];tr=a[ids,best]
        n=np.cross(tr[:,2]-tr[:,0],tr[:,1]-tr[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1),1e-10)[:,None]
        closest.append(cp);normals.append(n);indices.append(t[ix[ids,best]])
    return np.concatenate(closest),np.concatenate(normals),np.concatenate(indices)
