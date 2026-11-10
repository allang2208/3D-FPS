"""Choose a temporally coherent, off-camera shoulder for each fixed wrist/forearm."""
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import gaussian_filter1d
from pathlib import Path
from fit_motion import unit
P=Path(__file__).resolve().parent
def fit(grip,side):
    raw=np.load(P/'Review'/f'{grip}-rig.npz')
    names=raw['names'].tolist();m=raw['mats']
    bone=lambda s:m[:,names.index(s+'_'+side)]
    u,e,h=map(lambda n:bone(n)[:,:3,3]*100,('upperarm','lowerarm','hand'))
    def rotations(b):
        r=b[:,:3,:3];return R.from_matrix(r/np.linalg.norm(r,axis=1,keepdims=True))
    distal=rotations(bone('lowerarm_twist_01'));fore=distal*distal[0].inv()
    initial=e[0]-u[0];axis=unit(initial)
    t1=unit(np.cross(axis,np.array([0.,1.,0.])));t2=np.cross(axis,t1)
    candidates=np.array([np.zeros(3)]+[(np.cos(theta)*t1+np.sin(theta)*t2)*np.deg2rad(ang) for ang in range(10,101,10) for theta in np.deg2rad(np.arange(0,360,12))])
    directions=R.from_rotvec(candidates).apply(initial)
    sign=1 if side=='r' else -1
    movement=np.sum((candidates[:,None]-candidates[None,:])**2,axis=2)*4800
    previous=None;parents=[];eye=np.array([0.,0.,0.])
    for i in range(len(m)):
        s=e[i]-fore[i].apply(directions)
        # Signed clearance of the shoulder cap from the bottom or its own side.
        clearance=np.maximum(-s[:,2]-.768*s[:,1],sign*s[:,0]-1.364*s[:,1])
        seg=e[i]-s
        closest=s+np.clip((-s*seg).sum(1)/(seg*seg).sum(1),0,1)[:,None]*seg
        # Keep the upper-arm shaft out of the near-camera centre and avoid
        # bringing the open shoulder ring into the first-person image.
        costs=(np.maximum(13-clearance,0)*20)**2+(np.maximum(28-np.linalg.norm(closest,axis=1),0)*11)**2
        costs+=np.sum(((s-u[0])*[.55,.65,.7])**2,axis=1)+np.sum(candidates**2,axis=1)*540
        costs+=(np.maximum(np.linalg.norm(candidates,axis=1)-np.deg2rad(58),0)*110)**2
        if i in (0,len(m)-1):costs[1:]+=1e8
        if previous is None:previous=costs;continue
        pair=previous[:,None]+movement;parents.append(np.argmin(pair,axis=0));previous=costs+pair.min(0)
    ids=[int(previous.argmin())]
    for q in reversed(parents):ids.append(int(q[ids[-1]]))
    values=gaussian_filter1d(candidates[np.array(ids[::-1])],2.4,axis=0,mode='nearest')
    values[0]=values[-1]=0
    return values.tolist()
if __name__=='__main__':
    import json
    (P/'shoulder-turns.json').write_text(json.dumps({grip:{s:fit(grip,s) for s in 'rl'} for grip in ('Standard','LongGrip')},separators=(',',':')))
