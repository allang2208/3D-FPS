"""Outboard hand transfers and a continuous, length-preserving left belt drape."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation,Slerp

def smooth(t,a,b):
    x=np.clip((t-a)/(b-a),0,1);return x*x*(3-2*x)

def hand_route(target,t,empty):
    def route(times,interior,end_rotation=None):
        start,end=times[0],times[-1]
        a,b=np.argmin(abs(t-start)),np.argmin(abs(t-end))
        points=np.asarray([target[a,:3,3],*interior,target[b,:3,3]])
        take=(t>=start)&(t<=end)
        target[take,:3,3]=PchipInterpolator(times,points)(t[take])
        scale=np.linalg.norm(target[:,:3,:3],axis=1)
        rotations=target[[a,b],:3,:3]/scale[[a,b],None,:]
        if end_rotation is not None:rotations[1]=end_rotation
        q=Slerp([0,1],Rotation.from_matrix(rotations))(smooth(t[take],start,end)).as_matrix()
        target[take,:3,:3]=q*scale[take,None,:]
    # Leave the grip to the left before passing the receiver's underside.
    route([.23,.36,.48,.59,.72],[[-7.5,-38.,-17.5],[-10.,-26.,-2.],[-8.,-12.,5.]])
    # Release above the feed, pass outside its box, then enter the grip from below.
    if empty:route([1.17,1.32,1.48,1.72],[[-11.,-34.,-6.],[-7.5,-40.,-19.]])
    else:route([2.00,2.16,2.34,2.62],[[-12.,-34.,-7.],[-7.5,-40.,-19.]])

def drape(changed,bind,centers,t,empty):
    for prefix in ('','New_'):
        weight=(1.-smooth(t,4.24-(.9 if empty else 0),4.52-(.9 if empty else 0))) if prefix else smooth(t,2.00,2.38)
        if not prefix and empty:continue # spent strip is hidden for the empty reload
        names=[prefix+f'PKM_Belt_{i:02d}' for i in range(9)]
        box=prefix+'PKM_Box';xf=changed[box]@np.linalg.inv(bind[box]);xi=np.linalg.inv(xf)
        p=np.stack([(xi@changed[n]@np.linalg.inv(bind[n])@centers[n])[:,:3] for n in names],axis=1)
        q=p.copy()
        # Tail cells 6..8 retain the authored box-mouth seat. Each remaining
        # span turns progressively downward on the outside/left of that seat.
        angles=np.radians([-94,-102,-116,-132,-145,-160])
        for i in range(5,-1,-1):
            old=p[:,i]-p[:,i+1];length=np.linalg.norm(old[:,[0,2]],axis=1)
            a=np.arctan2(old[:,2],old[:,0]);delta=(angles[i]-a+np.pi)%(2*np.pi)-np.pi
            angle=a+delta*weight
            edge=old.copy();edge[:,0]=np.cos(angle)*length;edge[:,2]=np.sin(angle)*length
            q[:,i]=q[:,i+1]+edge
        for i,n in enumerate(names):
            lo,hi=max(i-1,0),min(i+1,8)
            _move(changed,n,xf,xi,p[:,i],q[:,i],p[:,hi]-p[:,lo],q[:,hi]-q[:,lo])
        for i in range(8):
            n=prefix+f'PKM_Belt_Link_{i:02d}'
            _move(changed,n,xf,xi,(p[:,i]+p[:,i+1])*.5,(q[:,i]+q[:,i+1])*.5,p[:,i+1]-p[:,i],q[:,i+1]-q[:,i])

def _move(changed,n,xf,xi,p,q,a,b):
    angle=np.arctan2(a[:,2]*b[:,0]-a[:,0]*b[:,2],a[:,0]*b[:,0]+a[:,2]*b[:,2])
    r=Rotation.from_rotvec(np.c_[angle*0,angle,angle*0]).as_matrix()
    m=np.broadcast_to(np.eye(4),(len(p),4,4)).copy();m[:,:3,:3]=r;m[:,:3,3]=q-(r@p[...,None])[:,:,0]
    changed[n]=xf@m@xi@changed[n]
