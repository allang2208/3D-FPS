"""NumPy adapter of ASH12Fix20260925/ash12_melee_fix.py::solve_side.

Rotate only the elbow bending plane on its exact two-bone circle. Shoulder,
wrist, fingers, gun, reach and bend angle stay unchanged. Helpers follow each
complete native segment; no skin changes or independent wrist corrections.
"""
import numpy as np
from scipy.spatial.transform import Rotation as R

def solve(p,ids,names,unit,swing,degrees):
    q=p.copy();u,l,h=[ids[n+'_r'] for n in ('upperarm','lowerarm','hand')]
    A,E,H=[p[j,:3,3].copy() for j in (u,l,h)]
    axis=unit(H-A);along=np.dot(E-A,axis)
    radial=E-A-axis*along
    newE=A+axis*along+R.from_rotvec(axis*np.radians(degrees)).apply(radial)
    for prefix,start,old_end,newstart,newend in [('upperarm',A,E,A,newE),('lowerarm',E,H,newE,H)]:
        delta=swing(old_end-start,newend-newstart)
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                q[j,:3,3]=newstart+delta@(p[j,:3,3]-start)
                q[j,:3,:3]=delta@p[j,:3,:3]
    return q

def shift_root(p,ids,names,unit,swing,shift):
    """Existing ASH/SVD optional root shift, with a fixed wrist and native lengths."""
    q=p.copy();c,u,l,h=[ids[n+'_r'] for n in ('clavicle','upperarm','lowerarm','hand')]
    A,E,H=[p[j,:3,3].copy() for j in (u,l,h)]
    L1=np.linalg.norm(E-A);L2=np.linalg.norm(H-E)
    newA=A+shift;axis=unit(H-newA);distance=np.linalg.norm(H-newA)
    along=(L1*L1-L2*L2+distance*distance)/(2*distance)
    pole=unit(E-newA-axis*np.dot(E-newA,axis))
    newE=newA+axis*along+pole*np.sqrt(max(0.,L1*L1-along*along))
    q[c,:3,3]+=shift
    for prefix,start,old_end,newstart,newend in [('upperarm',A,E,newA,newE),('lowerarm',E,H,newE,H)]:
        delta=swing(old_end-start,newend-newstart)
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                q[j,:3,3]=newstart+delta@(p[j,:3,3]-start)
                q[j,:3,:3]=delta@p[j,:3,:3]
    return q
