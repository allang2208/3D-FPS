from pathlib import Path
import pickle
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
r=Path(__file__).resolve().parent
def matrix(v):
    v=np.asarray(v);m=np.zeros((*v.shape[:-1],4,4));m[...,3,3]=1
    m[...,:3,:3]=R.from_quat(v[...,3:7].reshape(-1,4)).as_matrix().reshape(*v.shape[:-1],3,3)*v[...,None,7:10]
    m[...,:3,3]=v[...,:3]
    return m
def rot(m): return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2)[...,None,:]
def unit(v): return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def compose(a,parents):
    w=matrix(a)
    for i,p in enumerate(parents):
        if p>=0:w[:,i]=w[:,p]@w[:,i]
    return w
def sample(values,times,at):
    v=np.array(values).reshape(-1,10);ts=np.array(times)
    # The runtime selects the later key at equal timestamps.
    keep=np.r_[ts[1:]!=ts[:-1],True];v=v[keep];ts=ts[keep]
    at=np.clip(at,ts[0],ts[-1]);out=np.zeros((len(at),10))
    for j in (0,1,2,7,8,9):out[:,j]=np.interp(at,ts,v[:,j])
    out[:,3:7]=Slerp(ts,R.from_quat(v[:,3:7]))(at).as_quat() if len(ts)>1 else v[0,3:7]
    return out
def layer(a,path,profile,names,times):
    a=a.copy();ix={n:i for i,n in enumerate(names)}
    c=next((c for c in profile['clips'] if c['base']==path),None)
    if c:
        if c.get('retained'):raise ValueError('Retained clip requires direct sampling')
        for track in c['tracks']:
            v=sample(track['values'],track['times'],times);i=ix[track['bone']]
            a[:,i,:3]+=v[:,:3];a[:,i,3:7]=(R.from_quat(v[:,3:7])*R.from_quat(a[:,i,3:7])).as_quat();a[:,i,7:]+=v[:,7:]
    return a
def encode(w,parents):
    a=w.copy()
    for i,p in enumerate(parents):
        if p>=0:a[:,i]=np.linalg.inv(w[:,p])@w[:,i]
    s=np.linalg.norm(a[:,:,:3,:3],axis=2)
    q=R.from_matrix(rot(a).reshape(-1,3,3)).as_quat().reshape(*a.shape[:2],4)
    for k in range(1,len(q)):
        q[k,np.sum(q[k-1]*q[k],axis=1)<0]*=-1
    return np.concatenate((a[:,:,:3,3],q,s),axis=-1)
def metrics(w,bind,names):
    ix={n:i for i,n in enumerate(names)};idx=[ix[n] for n in ('upperarm_l','lowerarm_l','lowerarm_twist_01_l','hand_l')]
    a,e,tw,h=[w[:,i,:3,3] for i in idx]
    f0=bind[idx[-1],:3,3]-bind[idx[1],:3,3]
    dh=rot(w[:,idx[-1]])@rot(bind[idx[-1]]).T
    dt=rot(w[:,idx[2]])@rot(bind[idx[2]]).T
    wrist=np.degrees(np.arccos(np.clip(np.sum(unit(h-e)*(dh@unit(f0)),axis=1),-1,1)))
    residual=R.from_matrix(dt.transpose(0,2,1)@dh);q=residual.as_quat()
    tau=np.degrees(2*np.arctan2(q[:,:3]@unit(f0),q[:,3]));tau=(tau+180)%360-180
    return dict(wrist_swing=wrist,wrist_residual_twist=tau,wrist_deformation_angle=np.degrees(residual.magnitude()))
