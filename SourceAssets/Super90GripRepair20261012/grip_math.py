import gzip,json,bisect
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
def load(name):return json.loads(gzip.decompress((O/(name+'.json.gz')).read_bytes()))
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))
def pack(m):
    p,q,s=m.decompose();return [*p,q.x,q.y,q.z,q.w,*s]
def sample(tr,time):
    times=tr['times'];values=tr['values']
    if time<=times[0] or len(times)==1:return values[:10]
    if time>=times[-1]:return values[-10:]
    b=bisect.bisect_right(times,time);a=b-1;t=(time-times[a])/(times[b]-times[a])
    x=values[a*10:a*10+10];y=values[b*10:b*10+10]
    q=Quaternion((x[6],*x[3:6])).slerp(Quaternion((y[6],*y[3:6])),t)
    return [*(Vector(x[:3]).lerp(Vector(y[:3]),t)),q.x,q.y,q.z,q.w,*(Vector(x[7:]).lerp(Vector(y[7:]),t))]
def pose(data,row,layer=None):
    local={n:list(v) for n,v in row['local'].items()}
    if layer:
        for tr in layer['tracks']:
            v=local[tr['bone']];d=sample(tr,row['time']);q=Quaternion((d[6],*d[3:6]))@Quaternion((v[6],*v[3:6]))
            local[tr['bone']]=[*(Vector(v[:3])+Vector(d[:3])),q.x,q.y,q.z,q.w,*(Vector(v[7:])+Vector(d[7:]))]
    world={}
    for n,v in local.items():
        par=data['parents'][n];world[n]=world[par]@matrix(v) if par else matrix(v)
    return world,local
def skinned(data,world):
    v=np.array(data['vertices']);out=np.zeros_like(v)
    for n,r in data['rest'].items():
        w=np.array([weights.get(n,0) for weights in data['weights']]);ids=np.flatnonzero(w)
        if not len(ids):continue
        m=np.array(world[n]@matrix(r).inverted());out[ids]+=(v[ids]@m[:3,:3].T+m[:3,3])*w[ids,None]
    return out
