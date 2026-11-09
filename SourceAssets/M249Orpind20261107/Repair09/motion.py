"""Native data-model composition helpers, shared by production and editable export."""
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
def unit(v):return v/max(np.linalg.norm(v),1.e-12)
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def matrix(v):
    m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.array(v[7:])[None,:];m[:3,3]=v[:3];return m
def blend(a,b,w):return a@R.from_rotvec(R.from_matrix(a.T@b).as_rotvec()*w).as_matrix()
def mix(a,b,w):
    m=np.eye(4);m[:3,3]=a[:3,3]*(1-w)+b[:3,3]*w
    m[:3,:3]=blend(rot(a),rot(b),w)*(np.linalg.norm(a[:3,:3],axis=0)*(1-w)+np.linalg.norm(b[:3,:3],axis=0)*w);return m
def ease(x):
    x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def turn(axis,angle):return R.from_rotvec(unit(axis)*angle).as_matrix()
def swing(a,b):
    a,b=unit(a),unit(b);return R.from_quat(np.r_[np.cross(a,b),1+a@b]).as_matrix()
def frame(a,h):
    a=unit(a);h=unit(h-a*(a@h));return np.stack((a,np.cross(h,a),h),axis=1)
def sample(values,times,t):
    i=max(0,min(len(times)-1,np.searchsorted(times,t,side='right')-1));v=np.array(values[i],dtype=float)
    if i==len(times)-1:return v
    w=np.clip((t-times[i])/(times[i+1]-times[i]),0,1);b=np.array(values[i+1]);v[:3]=(1-w)*v[:3]+w*b[:3];v[7:]=(1-w)*v[7:]+w*b[7:]
    v[3:7]=R.from_matrix(blend(R.from_quat(v[3:7]).as_matrix(),R.from_quat(b[3:7]).as_matrix(),w)).as_quat();return v
def compose(names,parents,locals):
    w={}
    for n in names:w[n]=w[parents[n]]@locals[n] if parents[n] else locals[n].copy()
    return w
def donor_pose(data,role,t):
    clip=data[role];count=len(clip['frames']);times=np.arange(count)/clip['fps'];local={}
    profile=next((p for p in data['profile'] if p['base']==clip['path']),None)
    delta={d['bone']:d for d in profile['tracks']} if profile else {}
    for i,n in enumerate(data['names']):
        value=sample(np.asarray(clip['frames'])[:,i],times,t)
        if n in delta:
            d=delta[n];dv=sample(np.array(d['values']).reshape(-1,10),d['times'],t)
            value[:3]+=dv[:3];value[3:7]=(R.from_quat(dv[3:7])*R.from_quat(value[3:7])).as_quat();value[7:]+=dv[7:]
        local[n]=matrix(value)
    return compose(data['names'],data['parents'],local),local
