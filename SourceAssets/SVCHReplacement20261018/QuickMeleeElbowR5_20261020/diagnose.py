"""Focused R4 elbow-frame diagnosis; immutable saved motion and V9 surfaces."""
from pathlib import Path
import sys,json,numpy as np
O=Path(__file__).resolve().parent
R4=O.parent/'QuickMeleeSVDChainR4_20261020'
sys.path.insert(0,str(O.parent/'QuickMeleeHandR3_20261019'))
import check_surfaces as s
from scipy.spatial.transform import Rotation as R

def rot(m):return s.rigid(m)[:3,:3]
def frame(axis,normal):
    x=s.unit(axis);z=s.unit(normal-x*(normal@x));y=np.cross(z,x)
    return np.column_stack([x,y,z])
def axial(a,b,axis):
    q=R.from_matrix(a@b.T).as_quat()
    if q[3]<0:q=-q
    return np.degrees(2*np.arctan2(q[:3]@s.unit(axis),q[3]))
u,l,h=[s.ids[n] for n in ('upperarm_r','lowerarm_r','hand_r')]
ru=s.ref[l,:3,3]-s.ref[u,:3,3];rf=s.ref[h,:3,3]-s.ref[l,:3,3]
hinge=s.unit(np.cross(ru,rf));FU=frame(ru,hinge);FF=frame(rf,hinge)

def metrics(p):
    upper=p[l,:3,3]-p[u,:3,3];fore=p[h,:3,3]-p[l,:3,3]
    normal=s.unit(np.cross(upper,fore));du=frame(upper,normal)@FU.T;df=frame(fore,normal)@FF.T
    result={'bend':float(np.degrees(np.arccos(np.clip(s.unit(upper)@s.unit(fore),-1,1))))}
    for n in ['upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r']:
        j=s.ids[n];d=rot(p[j])@rot(s.ref[j]).T
        result[n]=float(axial(d,du if n.startswith('upper') else df,upper if n.startswith('upper') else fore))
    return result

if __name__=='__main__':
    poses=np.load(R4/'poses.npz')['base'];before=np.load(R4/'poses-before-elbow-support.npz')['base']
    rows=[{'frame':i,'R4':metrics(p),'before_support':metrics(before[i])} for i,p in enumerate(poses)]
    changes={}
    for n in ['upperarm_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_02_r']:
        j=s.ids[n];q=R.from_matrix(s.rigid(poses[:,j])[:,:3,:3])*R.from_matrix(s.rigid(before[:,j])[:,:3,:3]).inv()
        steps=np.degrees((q[1:]*q[:-1].inv()).magnitude());k=int(np.argmax(steps))
        changes[n]={'frame':k+1,'degrees_per_frame':float(steps[k])}
    (O/'diagnosis.json').write_text(json.dumps({'frames':rows,'correction_steps':changes},indent=2))
    print(json.dumps({'samples':[rows[i] for i in [0,12,20,40,60,70,90,108]],'correction_steps':changes},indent=2))
