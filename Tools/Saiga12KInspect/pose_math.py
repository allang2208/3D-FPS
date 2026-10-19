"""UE local transforms and sparse grip layers, in the saved native rig units."""
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

def matrix(v):
    m=np.eye(4)
    m[:3,:3]=Rot.from_quat(v[3:7]).as_matrix()*v[7:10]
    m[:3,3]=v[:3]
    return m

def rotation(m):
    return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)

def pack(m):
    scale=np.linalg.norm(m[:3,:3],axis=0)
    return np.r_[m[:3,3],Rot.from_matrix(m[:3,:3]/scale).as_quat(),scale]

def world(local,parents):
    result={}
    def resolve(n):
        if n not in result:
            p=parents[n]
            result[n]=resolve(p)@local[n] if p else local[n].copy()
        return result[n]
    for n in local:resolve(n)
    return result

def delta_at(track,time):
    times=np.asarray(track['times']);values=np.asarray(track['values']).reshape(-1,10)
    if len(times)==1 or time<=times[0]:return values[0].copy()
    if time>=times[-1]:return values[-1].copy()
    k=np.searchsorted(times,time)-1
    a=(time-times[k])/(times[k+1]-times[k])
    v=values[k]*(1-a)+values[k+1]*a
    v[3:7]=Slerp([0,1],Rot.from_quat(values[k:k+2,3:7]))([a]).as_quat()[0]
    return v

def apply(local,clip,time):
    result={n:m.copy() for n,m in local.items()}
    if clip:
        for track in clip['tracks']:
            n=track['bone'];v=pack(result[n]);d=delta_at(track,time)
            v[:3]+=d[:3];v[3:7]=(Rot.from_quat(d[3:7])*Rot.from_quat(v[3:7])).as_quat();v[7:]+=d[7:]
            result[n]=matrix(v)
    return result

def role(profile,name):
    return next((c for c in profile['clips'] if c['base'].endswith('_'+name)),None)
