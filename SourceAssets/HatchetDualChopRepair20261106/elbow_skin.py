"""Third-person anatomical skin support. Never used by the first-person rigs.

The primary chain and grip stay authored. The weighted elbow helpers follow the
achieved hinge instead of retaining their pre-repair world orientations.
"""
import numpy as np
from scipy.spatial.transform import Rotation as R

def unit(v): return v/max(np.linalg.norm(v),1.e-10)
def mix(a,b,t): return R.from_rotvec((b*a.inv()).as_rotvec()*t)*a

def fit_elbow_skin(frames,data,weights,twist_anchor=None,sides=('r','l')):
    from author import world
    names=data['names'];parents=data['parents'];idx={n:i for i,n in enumerate(names)}
    bind=world(np.array(data['reference']),parents)
    poses=np.array([world(f,parents) for f in frames]);target=poses.copy()
    def subtree(root):
        out=[]
        for i in range(len(names)):
            p=i
            while p>=0:
                if p==root:out.append(i);break
                p=parents[p]
        return out
    changed=set();anchors={}
    for side in sides:
        up,lo,hand=[idx[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        upper=idx['upperarm_twist_02_'+side]
        upper_helpers=subtree(upper)
        joint_helpers=subtree(idx['lowerarm_correctiveRoot_'+side])
        forearm_helpers=[idx['lowerarm_twist_'+suffix+'_'+side] for suffix in ('02','01')]
        changed.update(upper_helpers+joint_helpers+forearm_helpers)
        uq0=R.from_quat(bind[up,3:7]);lq0=R.from_quat(bind[lo,3:7]);hq0=R.from_quat(bind[hand,3:7])
        palm=[]
        for pose in poses:
            lower=R.from_quat(pose[lo,3:7])*lq0.inv()
            q=(R.from_quat(pose[hand,3:7])*(lower*hq0).inv()).as_quat()
            axis=unit(pose[hand,:3]-pose[lo,:3])
            palm.append(2*np.arctan2(np.dot(q[:3],axis),q[3]))
        palm=np.unwrap(palm)
        reference=twist_anchor[side] if twist_anchor else (palm[0]+np.pi)%(2*np.pi)-np.pi
        palm+=2*np.pi*round((reference-palm[0])/(2*np.pi));anchors[side]=float(palm[-1])
        for j,pose in enumerate(poses):
            u=R.from_quat(pose[up,3:7])*uq0.inv()
            l=R.from_quat(pose[lo,3:7])*lq0.inv()
            forearm=unit(pose[hand,:3]-pose[lo,:3])
            for bone in upper_helpers+joint_helpers+forearm_helpers:
                name=names[bone]
                # A short support zone bridges the joint; distal forearm bones
                # receive progressively more palm roll, as in radius/ulna rotation.
                if bone in joint_helpers:
                    deform=mix(u,l,.50)
                elif bone in forearm_helpers:
                    along=np.dot(bind[bone,:3]-bind[lo,:3],unit(bind[hand,:3]-bind[lo,:3]))
                    station=np.clip(along/np.linalg.norm(bind[hand,:3]-bind[lo,:3]),0,1)
                    deform=R.from_rotvec(forearm*palm[j]*station)*l
                elif name.startswith('upperarm_twistCor_02'):
                    deform=mix(u,l,.12)
                else:
                    deform=u
                goal_q=deform*R.from_quat(bind[bone,3:7])
                goal_p=pose[lo,:3]+deform.apply(bind[bone,:3]-bind[lo,:3])
                target[j,bone,:3]=pose[bone,:3]*(1-weights[j])+goal_p*weights[j]
                target[j,bone,3:7]=mix(R.from_quat(pose[bone,3:7]),goal_q,weights[j]).as_quat()
            # Kaitlin's twistCor_02_l translation is skeleton-retargeted to its
            # coincident parent. Carry the support displacement on twist_02;
            # re-express its other children below so their achieved world poses
            # are unchanged. No shared Skeleton retarget setting is modified.
            cor=idx['upperarm_twistCor_02_'+side]
            target[j,upper,:3]=target[j,cor,:3]-R.from_quat(target[j,upper,3:7]).apply(frames[j,cor,:3]*target[j,upper,7:])
    out=frames.copy()
    # Only helper locals may change. Hands, fingers, primary bone lengths,
    # shoulders, root, and all gameplay/contact clocks remain exact.
    for j,w in enumerate(target):
        for bone in sorted(changed):
            p=parents[bone];pq=R.from_quat(w[p,3:7])
            out[j,bone,:3]=pq.inv().apply(w[bone,:3]-w[p,:3])/w[p,7:]
            out[j,bone,3:7]=(pq.inv()*R.from_quat(w[bone,3:7])).as_quat()
    return out,anchors
