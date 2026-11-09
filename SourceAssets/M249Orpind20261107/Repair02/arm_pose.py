"""Whole-arm retargeting in native component space, including every skin helper."""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import gaussian_filter1d

def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)

def rot(m):
    return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2,keepdims=True)

def between(a,b):
    a,b=unit(a),unit(b)
    q=np.concatenate((np.cross(a,b),1+np.sum(a*b,axis=-1,keepdims=True)),axis=-1)
    return Rotation.from_quat(q).as_matrix()

def basis(axis,up):
    axis=unit(axis)
    up=unit(up-axis*np.sum(axis*up,axis=-1,keepdims=True))
    return np.stack((axis,np.cross(up,axis),up),axis=-1)

def bounded_rotations(quaternions):
    rotations=list(Rotation.from_quat(quaternions))
    limit=np.radians(7.)
    for indices in (range(1,len(rotations)),range(len(rotations)-2,-1,-1)):
        direction=1 if indices.step>0 else -1
        for i in indices:
            previous=rotations[i-direction]
            delta=(previous.inv()*rotations[i]).as_rotvec()
            angle=np.linalg.norm(delta)
            if angle>limit:rotations[i]=previous*Rotation.from_rotvec(delta*(limit/angle))
    return np.asarray([r.as_matrix() for r in rotations])

def solve(side,pose,bind,hand):
    upper,lower,wrist=[n+"_"+side for n in ("upperarm","lowerarm","hand")]
    S,E,H=[pose[n][:,:3,3] for n in (upper,lower,wrist)]
    S0,E0,H0=[bind[n][:3,3] for n in (upper,lower,wrist)]
    U0,F0=E0-S0,H0-E0
    hinge=unit(np.cross(U0,F0))
    Uframe,Fframe=basis(U0,hinge),basis(F0,hinge)
    hand=hand.copy()
    # Remove short discontinuities in the inherited authoring curve before IK.
    q=Rotation.from_matrix(rot(hand)).as_quat()
    q*=np.cumprod(np.r_[1,np.where(np.sum(q[1:]*q[:-1],axis=1)<0,-1,1)])[:,None]
    q=gaussian_filter1d(q,8.,axis=0,mode="nearest")
    hand[:,:3,:3]=bounded_rotations(q)*np.linalg.norm(hand[:,:3,:3],axis=1)[:,None,:]
    target=gaussian_filter1d(hand[:,:3,3],2.,axis=0,mode="nearest")
    l1=np.linalg.norm(E-S,axis=1)
    l2=np.linalg.norm(H-E,axis=1)
    axis=unit(target-S)
    distance=np.clip(np.linalg.norm(target-S,axis=1),np.abs(l1-l2)+.1,l1+l2-.4)
    wristpos=S+distance[:,None]*axis
    center=S+axis*((l1*l1-l2*l2+distance*distance)/(2*distance))[:,None]
    radius=np.sqrt(np.maximum(l1*l1-np.sum((center-S)**2,axis=1),0))
    radial=unit(E-center-axis*np.sum((E-center)*axis,axis=1,keepdims=True))
    radial=gaussian_filter1d(radial,5.,axis=0,mode="nearest")
    radial=unit(radial-axis*np.sum(radial*axis,axis=1,keepdims=True))
    # Choose a bounded swivel from the source elbow plane. Penalize wrist folding
    # as well as pronation, then smooth the angle before constructing any bones.
    desired=rot(hand)@rot(bind[wrist]).T
    candidates=np.radians(np.arange(-135,136,3))
    chosen=[]
    for i in range(len(S)):
        elbow=center[i]+Rotation.from_rotvec(candidates[:,None]*axis[i]).apply(radial[i])*radius[i]
        u,f=elbow-S[i],wristpos[i]-elbow
        h=unit(np.cross(u,f))
        fore=basis(f,h)@Fframe.T
        q=Rotation.from_matrix(np.swapaxes(fore,1,2)@desired[i]).as_quat()
        twist=2*np.arctan2(q[:,:3]@unit(F0),q[:,3])
        twist=(twist+np.pi)%(2*np.pi)-np.pi
        wrist_axis=desired[i]@unit(F0)
        bend=np.arccos(np.clip(unit(f)@wrist_axis,-1,1))
        cost=4.*bend*bend+1.6*twist*twist+.14*candidates*candidates
        chosen.append(candidates[np.argmin(cost)])
    swivel=gaussian_filter1d(chosen,8,mode="nearest")
    elbow=center+Rotation.from_rotvec(swivel[:,None]*axis).apply(radial)*radius[:,None]
    u,f=elbow-S,wristpos-elbow
    hinge_now=unit(np.cross(u,f))
    source_hinge=unit(np.cross(E-S,H-E))
    upper_delta=basis(u,hinge_now)@np.swapaxes(basis(E-S,source_hinge),1,2)
    fore_delta=basis(f,hinge_now)@np.swapaxes(basis(H-E,source_hinge),1,2)
    out={}
    for base,origin,oldorigin,oldaxis,newaxis,delta,source_origin in (
        ("upperarm",S,S0,U0,u,upper_delta,S),("lowerarm",elbow,E0,F0,f,fore_delta,E)):
        for suffix in ("","_twist_01","_twist_02"):
            n=base+suffix+"_"+side
            station=np.dot(bind[n][:3,3]-oldorigin,oldaxis)/np.dot(oldaxis,oldaxis)
            old_segment=E-S if base=="upperarm" else H-E
            offset=pose[n][:,:3,3]-source_origin-station*old_segment
            m=pose[n].copy()
            m[:,:3,3]=origin+station*newaxis+(delta@offset[...,None])[...,0]
            q=Rotation.from_matrix(delta@rot(pose[n])).as_quat()
            q*=np.cumprod(np.r_[1,np.where(np.sum(q[1:]*q[:-1],axis=1)<0,-1,1)])[:,None]
            q=gaussian_filter1d(q,5.,axis=0,mode="nearest")
            m[:,:3,:3]=bounded_rotations(q)*np.linalg.norm(pose[n][:,:3,:3],axis=1)[:,None,:]
            out[n]=m
    out[wrist]=hand.copy()
    out[wrist][:,:3,3]=wristpos
    return out
