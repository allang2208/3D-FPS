import json
from pathlib import Path
import numpy as np
O=Path(__file__).parent
FLIP=np.array([.01,-.01,.01])
def read(key):
    with (O/'Input'/(key+'.bin')).open('rb') as f:
        h=json.loads(f.readline());v,t=h['vertices'],h['triangles']
        p=np.fromfile(f,np.float32,v*3).reshape(v,3)
        tri=np.fromfile(f,np.int32,t*3).reshape(t,3)
        mat=np.fromfile(f,np.int32,t)
        uv=np.fromfile(f,np.float32,t*6).reshape(t,3,2)
        n=np.fromfile(f,np.float32,t*9).reshape(t,3,3)
    return h,p,tri,mat,uv,n
def transform(points,matrix):return points@matrix[:3,:3].T+matrix[:3,3]
def section(p,t,z,count=128):
    points=p[t];hits=[];mask=(points[:,:,2].min(1)<z)&(points[:,:,2].max(1)>z);points=points[mask]
    for f in points:
        row=[]
        for j in range(3):
            a,b=f[j],f[(j+1)%3]
            if (a[2]-z)*(b[2]-z)<0:row.append(a+(b-a)*(z-a[2])/(b[2]-a[2]))
        if len(row)==2:hits.append(row)
    segments=np.asarray(hits)[:,:,:2];center=(segments.min((0,1))+segments.max((0,1)))*.5
    a,b=segments[:,0]-center,segments[:,1]-center;e=b-a;cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
    result=[]
    for angle in np.linspace(0,2*np.pi,count,endpoint=False):
        d=np.array([np.cos(angle),np.sin(angle)]);den=cross(d,e);valid=np.abs(den)>1e-12
        dist=np.divide(cross(a,e),den,out=np.zeros(len(den)),where=valid);u=np.divide(cross(a,d),den,out=np.zeros(len(den)),where=valid)
        valid&=(dist>0)&(u>=0)&(u<=1)
        if not valid.any():raise RuntimeError('Missing cross section ray '+str(angle))
        result.append([*(center+dist[valid].max()*d),z])
    return np.array(result)
def body():
    h,p,t,m,uv,n=read('Body');b=json.loads((O/'Input/Body_bones.json').read_text())
    frames=json.loads((O/'Input/frames.json').read_text())['bind_to_root']
    names=np.array(b['bones']);bone=names[np.maximum(0,b['dominant'])]
    seated=p.astype(np.float64)*FLIP;normals=n.astype(np.float64)*[1,-1,1]
    for name,matrix in frames.items():
        matrix=np.array(matrix);sel=bone==name;faces=sel[t[:,0]]
        seated[sel]=transform(seated[sel],matrix)
        normals[faces]=normals[faces]@matrix[:3,:3].T
    return h,p,seated,t,m,uv,normals,bone
