"""Third-person Falcon pull: fixed weapon grips, continuous anatomical elbow arc."""
import numpy as np
from scipy.spatial.transform import Rotation as R
from author import world,unit,swing,basis,ease,continuous
from elbow_skin import fit_elbow_skin,mix

def repair_pull(frames,data,dual):
    names=data['names'];parents=data['parents'];idx={n:i for i,n in enumerate(names)}
    bind=world(np.array(data['reference']),parents);poses=np.array([world(f,parents) for f in frames]);target=poses.copy()
    ts=np.arange(len(frames))/60;weights=ease((ts-41/60)/(8/60))*(1-ease((ts-1.25)/.35))
    sides=('r','l') if dual else ('r',);metrics={}
    for side in sides:
        up,lo,h=[idx[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        bu=bind[lo,:3]-bind[up,:3];bf=bind[h,:3]-bind[lo,:3];bh=unit(np.cross(bu,bf))
        angles=[];previous=0.
        for w in poses:
            s,e,hand=w[[up,lo,h],:3];axis=unit(hand-s);center=s+axis*np.dot(e-s,axis);pole=e-center
            best=(float('inf'),0.)
            for degrees in range(-90,91,3):
                goal=center+R.from_rotvec(axis*np.radians(degrees)).apply(pole)
                if np.linalg.norm(goal-e)>15.:continue
                upper=goal-s;lower=hand-goal;hinge=unit(np.cross(upper,lower))
                delta=R.from_matrix(basis(lower,hinge)@basis(bf,bh).T)
                q=(R.from_quat(w[h,3:7])*(delta*R.from_quat(bind[h,3:7])).inv()).as_quat()
                roll=(np.degrees(2*np.arctan2(np.dot(q[:3],unit(lower)),q[3]))+180)%360-180
                # Keep the elbow below its shoulder and outside the ribs;
                # share palm orientation with the elbow arc before twisting skin.
                chest=w[idx['spine_05'],:3]
                outside=(-1 if side=='r' else 1)*(goal[0]-chest[0])
                cost=.025*degrees*degrees+.03*(degrees-previous)**2+1.2*max(0,abs(roll)-80)**2+3*max(0,goal[2]-s[2]+12)**2+8*max(0,13-outside)**2
                if cost<best[0]:best=(cost,float(degrees))
            previous=best[1];angles.append(previous)
        angles=np.convolve(np.pad(angles,(2,2),mode='edge'),[.1,.2,.4,.2,.1],mode='valid')*weights
        moved=[]
        for j,w in enumerate(poses):
            s,e,hand=w[[up,lo,h],:3];axis=unit(hand-s);center=s+axis*np.dot(e-s,axis)
            goal=center+R.from_rotvec(axis*np.radians(angles[j])).apply(e-center)
            upper=goal-s;lower=hand-goal;hinge=unit(np.cross(upper,lower))
            uq=R.from_matrix(basis(upper,hinge)@basis(bu,bh).T)*R.from_quat(bind[up,3:7])
            lq=R.from_matrix(basis(lower,hinge)@basis(bf,bh).T)*R.from_quat(bind[lo,3:7])
            transported_u=swing(e-s,upper)*R.from_quat(w[up,3:7])
            transported_l=swing(hand-e,lower)*R.from_quat(w[lo,3:7])
            target[j,up,3:7]=mix(transported_u,uq,weights[j]).as_quat()
            target[j,lo,:3]=goal;target[j,lo,3:7]=mix(transported_l,lq,weights[j]).as_quat()
            moved.append(np.linalg.norm(goal-e))
        metrics[side]=dict(max_elbow_reposition_cm=float(max(moved)))
    out=frames.copy()
    # Re-express only main-chain rotations; unchanged local translations keep
    # exact native bone lengths, wrist positions and weapon orientations.
    for j,w in enumerate(target):
        for side in sides:
            for stem in ('upperarm','lowerarm','hand'):
                b=idx[stem+'_'+side];p=parents[b]
                out[j,b,3:7]=(R.from_quat(w[p,3:7]).inv()*R.from_quat(w[b,3:7])).as_quat()
    out,_=fit_elbow_skin(out,data,weights,sides=sides)
    # Follow the humerus at the shoulder as well as the distal elbow helpers.
    # Old corrective locals were compensating for the rejected axial roll.
    after=np.array([world(f,parents) for f in out]);support=[]
    for side in sides:
        roots=[idx['upperarm_correctiveRoot_'+side],idx['upperarm_twist_01_'+side]]
        for i in range(len(names)):
            p=i
            while p>=0:
                if p in roots:support.append((i,side));break
                p=parents[p]
    fixed=after.copy()
    for j,w in enumerate(after):
        for b,side in support:
            up=idx['upperarm_'+side]
            deform=R.from_quat(w[up,3:7])*R.from_quat(bind[up,3:7]).inv()
            goal_q=deform*R.from_quat(bind[b,3:7]);goal_p=w[up,:3]+deform.apply(bind[b,:3]-bind[up,:3])
            fixed[j,b,:3]=w[b,:3]*(1-weights[j])+goal_p*weights[j]
            fixed[j,b,3:7]=mix(R.from_quat(w[b,3:7]),goal_q,weights[j]).as_quat()
    for j,w in enumerate(fixed):
        for b,_ in support:
            p=parents[b];q=R.from_quat(w[p,3:7]);out[j,b,:3]=q.inv().apply(w[b,:3]-w[p,:3])/w[p,7:]
            out[j,b,3:7]=(q.inv()*R.from_quat(w[b,3:7])).as_quat()
    # The cut, the low hold and both outer transition endpoints stay untouched.
    out[weights<1.e-9]=frames[weights<1.e-9]
    return continuous(out),metrics
