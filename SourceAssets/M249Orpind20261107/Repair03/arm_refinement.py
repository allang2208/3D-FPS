"""Contact-preserving wrist limits and V9 anatomical elbow / forearm frames."""
import importlib.util
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

spec=importlib.util.spec_from_file_location('m249_reach',Path(__file__).with_name('reach.py'))
reach=importlib.util.module_from_spec(spec);spec.loader.exec_module(reach)
unit,rot,basis=reach.unit,reach.rot,reach.basis
def turn(axis,angle):return Rotation.from_rotvec(unit(axis)*angle[:,None]).as_matrix()
def swing(a,b):
    a,b=unit(a),unit(b)
    return Rotation.from_quat(np.c_[np.cross(a,b),1+np.sum(a*b,axis=1)]).as_matrix()

def solve(side,pose,bind,hand,pivot=None,working=None,limit=None):
    upper,lower,wrist=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    U0=bind[lower][:3,3]-bind[upper][:3,3];F0=bind[wrist][:3,3]-bind[lower][:3,3]
    H0=unit(np.cross(U0,F0));FU0=basis(U0,H0);FL0=basis(F0,H0)
    out=reach.solve(side,pose,bind,hand)
    if pivot is not None and working is not None and np.max(working)>.001:
        pin=(hand@pivot[...,None])[:,:3,0]
        threshold=np.radians(limit if limit is not None else np.full(len(hand),40.))
        for _ in range(2):
            desired=rot(out[wrist])@rot(bind[wrist]).T@unit(F0)
            fore=unit(out[wrist][:,:3,3]-out[lower][:,:3,3])
            angle=np.arccos(np.clip(np.sum(desired*fore,axis=1),-1,1))
            correction=Rotation.from_matrix(swing(desired,fore)).as_rotvec()
            fraction=np.maximum(0.,angle-threshold)/np.maximum(angle,1e-8)*working
            target=out[wrist].copy()
            target[:,:3,:3]=Rotation.from_rotvec(correction*fraction[:,None]).as_matrix()@target[:,:3,:3]
            target[:,:3,3]=pin-(target[:,:3,:3]@pivot[:,:3,None])[:,:,0]
            out=reach.solve(side,pose,bind,target)
    S,E,H=[out[n][:,:3,3] for n in (upper,lower,wrist)]
    u,f=E-S,H-E;hinge=unit(np.cross(u,f))
    bend=np.arccos(np.clip(np.sum(unit(u)*unit(f),axis=1),-1,1))
    for i in range(1,len(hinge)):
        if bend[i]<np.radians(30):
            carry=hinge[i-1]-unit(u[i])*np.dot(unit(u[i]),hinge[i-1])
            w=np.clip((np.degrees(bend[i])-10.)/20.,0.,1.);w=w*w*(3-2*w)
            hinge[i]=unit(w*hinge[i]+(1-w)*unit(carry))
    crease=np.clip((np.degrees(bend)-30.)/40.,0.,1.);crease=crease*crease*(3-2*crease)
    anatomical=turn(f,np.radians(20 if side=='l' else -20)*crease)@basis(f,hinge)@FL0.T
    dh=rot(out[wrist])@rot(bind[wrist]).T
    q=Rotation.from_matrix(np.swapaxes(anatomical,1,2)@dh).as_quat()
    q*=np.where(q[:,3:4]<0,-1,1)
    roll=np.unwrap(2*np.arctan2(q[:,:3]@unit(F0),q[:,3]))
    roll-=2*np.pi*round(float(np.mean(roll)/(2*np.pi)))
    roll=np.where(roll>np.radians(210),roll-2*np.pi,np.where(roll<np.radians(-210),roll+2*np.pi,roll))
    fore_roll=np.clip(roll,-np.radians(110),np.radians(110))
    elbow_frame=turn(f,roll-fore_roll)@anatomical
    upper_frame=swing(elbow_frame@U0,u)@elbow_frame
    for base,origin,rest_origin,rest_axis,axis,frame in (
        ('upperarm',S,bind[upper][:3,3],U0,u,upper_frame),
        ('lowerarm',E,bind[lower][:3,3],F0,f,elbow_frame)):
        for suffix,share in (('',0.),('_twist_01',1.),('_twist_02',.5)):
            n=base+suffix+'_'+side
            station=np.dot(bind[n][:3,3]-rest_origin,rest_axis)/np.dot(rest_axis,rest_axis)
            offset=bind[n][:3,3]-rest_origin-station*rest_axis
            delta=turn(f,fore_roll*share)@frame if base=='lowerarm' else frame
            m=out[n].copy();m[:,:3,:3]=(delta@rot(bind[n]))*np.linalg.norm(m[:,:3,:3],axis=1)[:,None,:]
            m[:,:3,3]=origin+station*axis+(delta@offset)
            out[n]=m
    return out
