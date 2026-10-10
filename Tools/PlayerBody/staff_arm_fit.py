"""Native arm support shared by staff strike and casting authors."""
import numpy as np
from scipy.spatial.transform import Rotation as R

def fit(rig,f,point,q,pole):
    ref,parents,ix=rig.ref,rig.parents,rig.ix
    hand,upper,lower=[ix[n] for n in ("hand_r","upperarm_r","lowerarm_r")]
    # Match FPSBodyStaffArmPose: solve the elbow from the actual palm's neutral
    # forearm direction, not a fixed donor pole with a wrist penalty afterward.
    w=rig.fk(f);origin=w[upper,:3];axis=rig.unit(point-origin)
    l1,l2=np.linalg.norm(ref[lower,:3]),np.linalg.norm(ref[hand,:3])
    distance=np.clip(np.linalg.norm(point-origin),abs(l1-l2)+.01,(l1+l2)*.965)
    point=origin+axis*distance
    a,b=rig.unit(ref[lower,:3]),rig.unit(ref[hand,:3])
    lower_ref,hand_ref=R.from_quat(ref[lower,3:7]),R.from_quat(ref[hand,3:7])
    expected=R.from_quat(q)*hand_ref.inv()
    ideal=point-expected.apply(b)*l2
    bend=rig.unit(ideal-origin-axis*np.dot(ideal-origin,axis))
    incoming=rig.unit(pole-axis*np.dot(pole,axis))
    bend=rig.unit(bend+incoming*.15)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=origin+axis*along+bend*np.sqrt(max(0.,l1*l1-along*along))
    udir,ldir=rig.unit(elbow-origin),rig.unit(point-elbow)
    normal=rig.unit(np.cross(udir,ldir));native_normal=rig.unit(np.cross(a,lower_ref.apply(b)))
    upper_q=R.from_quat(rig.frame_xy(udir,normal))*R.from_quat(rig.frame_xy(a,native_normal)).inv()
    lower_q=upper_q*lower_ref
    old=lower_q.apply(b);cross=np.cross(old,ldir)
    lower_q=R.from_rotvec(rig.unit(cross)*np.arctan2(np.linalg.norm(cross),np.dot(old,ldir)))*lower_q
    difference=(expected*lower_q.inv()).as_quat()
    if difference[3]<0:difference=-difference
    roll=2*np.arctan2(np.dot(difference[:3],ldir),difference[3])
    lower_q=R.from_rotvec(ldir*np.clip(roll,np.deg2rad(-85),np.deg2rad(85)))*lower_q
    neutral=(lower_q*hand_ref).as_quat()
    wrist=(R.from_quat(neutral).inv()*R.from_quat(q)).magnitude()
    actual=rig.slerp(neutral,q,min(1.,np.deg2rad(25)/max(wrist,1e-9)))
    f[upper,3:7]=rig.mul(rig.inv(w[parents[upper],3:7]),upper_q.as_quat())
    f[lower,3:7]=(upper_q.inv()*lower_q).as_quat()
    f[hand,3:7]=(lower_q.inv()*R.from_quat(actual)).as_quat()
    return f
