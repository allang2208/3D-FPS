"""Fit each articulated finger against the measured Fab shaft while retaining the equip and breathing tracks."""
import json
import os
import sys
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares

root=Path(os.environ["FPS_PROJECT_ROOT"])
family=root/"SourceAssets/WoodenTorch20261122"
out=family/"FabHandheldR2/Export"
sys.path.insert(0,str(root/"SourceAssets/Kukri20261020"))
from kmath import Rig, T, load_dump, qmul

fit=json.loads((out/"fit.json").read_text())
carry=json.loads((family/"Export/Carry.json").read_text())
rig=Rig(load_dump())
pose=rig.world({b:T(*v) for b,v in carry["frames"][carry["raise_frames"]].items()})
left=json.loads((root/"SourceAssets/DualKukriIdle20261025/left_kukri.json").read_text())["rel_to_hand_l"]
samples=360
angles=np.arange(samples)*2*np.pi/samples
rays=np.c_[np.cos(angles),np.sin(angles)]

class Surface:
    def __init__(self,sections):
        self.z=np.array([s[0] for s in sections])
        radii=[]
        for _,points in sections:
            planes=ConvexHull(points).equations
            denom=planes[:,:2]@rays.T
            intersections=-planes[:,2,None]/np.maximum(denom,1e-7)
            radii.append(np.min(np.where(denom>1e-7,intersections,np.inf),axis=0))
        self.radii=np.array(radii)
    def gap(self,points):
        i=np.clip((points[:,2]-self.z[0])/(self.z[1]-self.z[0]),0,len(self.z)-1.00001)
        a=(np.arctan2(points[:,1],points[:,0])*samples/(2*np.pi))%samples
        lo=i.astype(int);col=a.astype(int);f=a-col
        interp=self.radii[:,col]*(1-f)+self.radii[:,(col+1)%samples]*f
        k=np.arange(len(points))
        return np.hypot(points[:,0],points[:,1])-((1-i+lo)*interp[lo,k]+(i-lo)*interp[lo+1,k])

def rotation(q):
    return Rotation.from_quat(q,scalar_first=True)

old=Surface(fit["old_profile_cm"])
new=Surface(fit["new_profile_cm"])
result={"sockets_ue_cm":{},"finger_local_deltas_wxyz":{}}
for side,sign in [("r",1),("l",-1)]:
    # Keep the near surface against the palm web as the new shaft is rounder.
    j=90 if side=="r" else 270
    palm_shift=sign*float(np.median(new.radii[9:20,j]-old.radii[9:20,j]))
    socket=np.array([0.,palm_shift,0.])
    result["sockets_ue_cm"]["Grip_"+side.upper()]=socket.tolist()
    grip=T(pose["WPN_root"].p,pose["WPN_root"].q) if side=="r" else T(left["location"],left["rotation_wxyz"])*T(pose["hand_l"].p,pose["hand_l"].q)
    for finger in ["thumb","index","middle","ring","pinky"]:
        names=[f"{finger}_0{i}_{side}" for i in range(1,4)]
        joints=[pose[n].relative_to(grip) for n in names]
        rot=[rotation(t.q) for t in joints]
        pos=np.array([t.p for t in joints])
        # The distal pad continues along the local phalanx axis after the last joint.
        distal=rot[2].apply(rot[1].inv().apply(pos[2]-pos[1]))*.76
        end=np.vstack((pos,pos[2]+distal))
        vec=np.diff(end,axis=0)
        axis=np.cross(vec[0],vec[1])
        axis/=np.linalg.norm(axis)
        flex=[r.inv().apply(axis) for r in rot]
        segments=[rot[k].inv().apply(vec[k]) for k in range(3)]
        def pads(angles,return_delta=False):
            p=pos[0].copy()
            rotations=[];coords=[]
            for k in range(3):
                r=rot[0] if k==0 else r*(rot[k-1].inv()*rot[k])
                delta=Rotation.from_rotvec(flex[k]*angles[k])
                r=r*delta; rotations.append(delta.as_quat(scalar_first=True))
                v=r.apply(segments[k])
                coords.extend([p+v*.35,p+v*.70,p+v])
                p=p+v
            return rotations if return_delta else np.array(coords)
        rest=pads(np.zeros(3))
        # Preserve the donor's skin-to-bone spacing, letting the distal finger pads settle on the new wood.
        radius=.65 if finger=="pinky" else .8
        target=np.maximum(old.gap(rest),radius)
        target[6:]=np.minimum(target[6:],radius+.32)
        weights=np.array([.3,.4,.5,.7,.8,.9,1.,1.1,1.2])
        def residual(x):
            current=pads(x)
            gap=new.gap(current+socket)
            return np.r_[(gap-target)*weights,2.*np.minimum(gap-radius,0.),x*.35,(current[-1,2]-rest[-1,2])*.20]
        solution=least_squares(residual,np.zeros(3),bounds=(-.73,.73))
        for name,dq in zip(names,pads(solution.x,True)):
            result["finger_local_deltas_wxyz"][name]=dq.tolist()
for frame in carry["frames"]:
    for name,dq in result["finger_local_deltas_wxyz"].items():
        frame[name][1]=qmul(frame[name][1],dq).tolist()
(out/"Carry.json").write_text(json.dumps(carry,separators=(",",":")),encoding="utf8")
(out/"hands.json").write_text(json.dumps(result,indent=2),encoding="utf8")
