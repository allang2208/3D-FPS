"""Rigid shoulder support with fixed hand, fixed bone lengths and elbow hinge."""
from clearance_context import *
def basis(axis,normal):
    x=unit(axis);z=unit(normal-x*(normal@x));return np.column_stack((x,np.cross(z,x),z))
def shift_shoulder(p,cam,offset):
    out=p.copy();A,E,H=[p[j,:3,3] for j in (ui,li,hi)]
    S=A+cam[:3,:3].T@np.asarray(offset);l1=np.linalg.norm(E-A);l2=np.linalg.norm(H-E)
    axis=unit(H-S);d=np.linalg.norm(H-S);reach=d/(l1+l2)
    if d>=l1+l2-.01 or d<=abs(l1-l2)+.01:return None,{'reach':reach}
    pole=unit(E-S-axis*((E-S)@axis));along=(l1*l1-l2*l2+d*d)/(2*d)
    elbow=S+axis*along+pole*np.sqrt(max(0,l1*l1-along*along))
    n0=np.cross(E-A,H-E);n1=np.cross(elbow-S,H-elbow)
    du=basis(elbow-S,n1)@basis(E-A,n0).T;dl=basis(H-elbow,n1)@basis(H-E,n0).T
    out[ci,:3,3]+=S-A
    for j,n in enumerate(names):
        if n.endswith('_l') and n.startswith('upperarm'):
            out[j,:3,3]=S+du@(p[j,:3,3]-A);out[j,:3,:3]=du@p[j,:3,:3]
        elif n.endswith('_l') and n.startswith('lowerarm'):
            out[j,:3,3]=elbow+dl@(p[j,:3,3]-E);out[j,:3,:3]=dl@p[j,:3,:3]
    # The palm remains exactly the current contact, including its rotation.
    # Compensate only the additional axial motion across native 100%/50% helpers.
    fo=R.from_matrix(rigid(p[li])[:3,:3]);fn=R.from_matrix(rigid(out[li])[:3,:3]);ho=R.from_matrix(rigid(p[hi])[:3,:3])
    delta=((fn.inv()*ho)*(fo.inv()*ho).inv()).as_quat()
    if delta[3]<0:delta=-delta
    local_axis=fo.inv().apply(unit(H-E));roll=2*np.arctan2(delta[:3]@local_axis,delta[3])
    for name,share in [('lowerarm_twist_01_l',1.),('lowerarm_twist_02_l',.5)]:
        j=ids[name];rot=fn*R.from_rotvec(local_axis*roll*share)*fn.inv();out[j,:3,:3]=rot.as_matrix()@out[j,:3,:3]
    swing_change=np.rad2deg(np.arccos(np.clip(unit(H-E)@unit(H-elbow),-1,1)))
    return out,{'reach':float(reach),'forearm_direction_change_deg':float(swing_change),'additional_axial_deg':float(np.rad2deg(roll)),'elbow_move_cm':float(np.linalg.norm(elbow-E))}
if __name__=='__main__':
    for role in ('reload','reload_empty'):
        for i in (64,72,168,176,208,240,264,280,304,328,352,368):
            p=pose(role,i);cam=cam_at(role,i);choices=[]
            for back in np.arange(0,10.1,.5):
                q,s=shift_shoulder(p,cam,[-back,0,0])
                if q is None or s['reach']>.97:continue
                margin=float(screen_margin(root_points(q,cam),21/9).min())
                choices.append((max(0,.12-margin),float(back),margin,s))
            if choices:
                pick=min(choices,key=lambda r:(r[0],r[1]));print(role,i,pick,flush=True)
