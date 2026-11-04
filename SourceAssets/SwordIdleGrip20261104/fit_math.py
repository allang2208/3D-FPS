import numpy as np
from scipy.spatial.transform import Rotation as R
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def rotation(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def matrix(v):
    m=np.eye(4);m[:3,:3]=R.from_quat(v['q']).as_matrix()*v['s'];m[:3,3]=v['p'];return m
def pack(m):return dict(p=m[:3,3].tolist(),q=R.from_matrix(rotation(m)).as_quat().tolist(),s=np.linalg.norm(m[:3,:3],axis=0).tolist())
def frame(u,f):
    u=unit(u);n=unit(np.cross(u,f));return np.column_stack([u,np.cross(n,u),n])
def fit_arm(pose,parents,side,delta,orientation=None):
    source={n:m.copy() for n,m in pose.items()};U,L,H=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
    a,e,h=[source[n][:3,3] for n in [U,L,H]];target=h+delta
    upper=np.linalg.norm(e-a);lower=np.linalg.norm(h-e);axis=unit(target-a);distance=np.linalg.norm(target-a)
    along=(upper*upper-lower*lower+distance*distance)/(2*distance)
    height=np.sqrt(max(0,upper*upper-along*along));pole=unit((e-a)-axis*np.dot(e-a,axis));elbow=a+axis*along+pole*height
    uq=frame(elbow-a,target-elbow)@frame(e-a,h-e).T@rotation(source[U])
    lq=frame(target-elbow,elbow-a)@frame(h-e,e-a).T@rotation(source[L])
    for n,p in parents.items():
        if n not in pose:continue
        if n==U:pose[n][:3,:3]=uq*np.linalg.norm(source[n][:3,:3],axis=0)
        elif n==L:
            pose[n][:3,3]=elbow;pose[n][:3,:3]=lq*np.linalg.norm(source[n][:3,:3],axis=0)
        elif n==H:
            pose[n][:3,3]=target
            if orientation is not None:pose[n][:3,:3]=orientation*np.linalg.norm(source[n][:3,:3],axis=0)
        else:
            ancestor=p
            while ancestor in parents and ancestor not in [U,L,H]:ancestor=parents[ancestor]
            if ancestor in [U,L,H] and p in pose:pose[n]=pose[p]@np.linalg.inv(source[p])@source[n]
    # Carry palm roll into the current V9 forearm helpers without adding it to the wrist.
    old_l=rotation(source[L]);old_h=rotation(source[H]);new_h=rotation(pose[H]);local_axis=old_l.T@unit(h-e)
    q=R.from_matrix((lq.T@new_h)@(old_l.T@old_h).T).as_quat();tau=2*np.arctan2(q[:3]@local_axis,q[3]);tau=(tau+np.pi)%(2*np.pi)-np.pi
    for suffix,share in [('01',1.),('02',.5)]:
        n='lowerarm_twist_'+suffix+'_'+side
        if n in pose:pose[n][:3,:3]=lq@R.from_rotvec(local_axis*tau*share).as_matrix()@old_l.T@source[n][:3,:3]
    return pose
def skin_matrices(pose,rest,names):return np.array([pose[n]@np.linalg.inv(rest[n]) for n in names])
def blend_matrices(bones,weights,matrices):
    result=np.zeros((len(bones),4,4))
    for k in range(bones.shape[1]):result+=matrices[bones[:,k]]*weights[:,k,None,None]
    return result
def point_digit(pose,parents,bone,next_bone,target):
    a=unit(pose[next_bone][:3,3]-pose[bone][:3,3]);b=unit(target)
    q=R.from_quat(np.r_[np.cross(a,b),1+np.dot(a,b)]).as_matrix()
    pivot=pose[bone][:3,3].copy();change=np.eye(4);change[:3,:3]=q;change[:3,3]=pivot-q@pivot
    for n in pose:
        parent=n
        while parent in parents and parent!=bone:parent=parents[parent]
        if parent==bone:pose[n]=change@pose[n]
