"""Object-space grip correction while retaining source 715 gesture and timing."""
import sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
sys.path.insert(0,str(Path(__file__).parent.parent/'RSH12Speedloader20261003'))
from contact_motion import carry_arm

def quat(v):return Quaternion((v[3],*v[:3]))
def correct(p,rig,meta,recipe,weight=1.):
    old={n:m.copy() for n,m in p.items()};side=recipe['side'];hn='hand_'+side
    frame=p['WPN_root']@Matrix(meta['alignment']);target=p[hn].copy()
    t,q,s=target.decompose();t+=frame.to_3x3()@Vector(recipe['offset_grip_m'])*weight
    target=Matrix.LocRotScale(t,q@Quaternion().slerp(quat(recipe['wrist_local_quat']),weight),s)
    changed=carry_arm(p,old,list(p),side,target)
    for n,v in recipe['finger_local_delta'].items():
        parent=rig.data.bones[n].parent.name
        lp=old[parent].inverted()@old[n];t,q,s=lp.decompose()
        p[n]=p[parent]@Matrix.LocRotScale(t,Quaternion().slerp(quat(v),weight)@q,s);changed.add(n)
    return changed
