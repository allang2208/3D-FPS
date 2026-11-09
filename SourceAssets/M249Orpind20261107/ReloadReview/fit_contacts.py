"""Fit the existing animated hand silhouettes to the visible moving strip in mesh space."""
import json
import pickle
from pathlib import Path
import numpy as np
from numba import njit
from scipy.spatial.transform import Rotation
from scipy.ndimage import gaussian_filter1d
from strand_fit import fit_strand, as_matrix
from clearance_field import ClearanceField

here = Path(__file__).resolve().parent
folder = here.parents[2] / "Saved/M249ReloadReview/before"
def load(name):
    with (folder / (name + ".pkl")).open("rb") as handle:
        return pickle.load(handle)

def matrices(rows):
    a = np.asarray(rows)
    out = np.broadcast_to(np.eye(4), (*a.shape[:-1], 4, 4)).copy()
    rotations = Rotation.from_quat(a[..., 3:7].reshape(-1, 4)).as_matrix()
    out[..., :3, :3] = rotations.reshape(*a.shape[:-1], 3, 3) * a[..., None, 7:]
    out[..., :3, 3] = a[..., :3]
    return out

@njit
def heightfield(points, faces, low, step, top):
    grid = np.full((190, 190), -np.inf)
    sign = 1 if top else -1
    for face in faces:
        a,b,c = points[face[0]], points[face[1]], points[face[2]]
        ab, ac = b-a, c-a
        det = ab[0]*ac[1] - ab[1]*ac[0]
        if abs(det) < 1e-9:
            continue
        x0 = max(0, int(np.ceil((min(a[0],b[0],c[0])-low[0])/step)))
        x1 = min(189, int(np.floor((max(a[0],b[0],c[0])-low[0])/step)))
        y0 = max(0, int(np.ceil((min(a[1],b[1],c[1])-low[1])/step)))
        y1 = min(189, int(np.floor((max(a[1],b[1],c[1])-low[1])/step)))
        for x in range(x0,x1+1):
            rx = low[0]+step*x-a[0]
            for y in range(y0,y1+1):
                ry = low[1]+step*y-a[1]
                u = (rx*ac[1]-ry*ac[0])/det
                v = (ry*ab[0]-rx*ab[1])/det
                if min(u,v,1-u-v) >= 0:
                    z = sign*(a[2]+u*ab[2]+v*ac[2])
                    grid[x,y] = max(grid[x,y],z)
    return grid

d = load("geometry")
names = d["names"]
indices = {b: i for i, b in enumerate(d["used"])}
verts = np.asarray(d["vertices"])
faces = np.asarray(d["faces"])
slots = np.asarray(d["sections"])
weights = d["weights"]
dom = np.array([indices[max(row,key=lambda w:w[1])[0]] for row in weights])
class Surface:
    def __init__(self, mask):
        self.ids, triangles = np.unique(faces[mask],return_inverse=True)
        self.faces = triangles.reshape(-1,3)
        groups = {}
        for i, vertex in enumerate(self.ids):
            for b,w in weights[vertex]:
                groups.setdefault(indices[b],[]).append((i,w))
        self.groups = []
        for b, pairs in groups.items():
            ii, w = np.array(pairs).T
            ii = ii.astype(int)
            coords = np.c_[verts[self.ids[ii]],np.ones(len(ii))] * w[:,None]
            self.groups.append((b,ii,coords))
    def skin(self, m):
        result = np.zeros((len(self.ids),3))
        for b,idx,p in self.groups:
            result[idx] += p @ m[b,:3].T
        return result

def ramp(t,a,b):
    u = np.clip((t-a)/(b-a),0,1)
    return u*u*(3-2*u)

bind = matrices(d["bind"])
invbind = np.linalg.inv(bind)
root = names.index("WPN_root")
idle = matrices(load("idle")[1][0]) @ invbind
idle = np.linalg.inv(idle[root]) @ idle
obstacles = {}
for name in ("WPN_root","PKM_Cover","PKM_Tray","PKM_Box"):
    index = names.index(name)
    ids, tri = np.unique(faces[dom[faces[:,0]]==index],return_inverse=True)
    obstacles[name] = ClearanceField(verts[ids],tri.reshape(-1,3))

def rotations(yaw,tilt):
    return Rotation.from_euler("zy",[yaw,tilt],degrees=True).as_matrix()

def place(surface, wrist, center, strip_top, low, yaw, tilt, lateral, weight, margin):
    rotated = (surface-wrist)@rotations(yaw*weight,tilt*weight).T+wrist
    finger = np.mean([rotated[mask].mean(axis=0) for mask in pads],axis=0)
    delta = center-finger
    delta[1] += lateral
    delta *= weight
    delta[2] = 0.
    palm = rotated+delta
    underside = heightfield(palm,hand.faces,low,.09,False)
    distance = np.max(strip_top+underside)
    if np.isfinite(distance):
        lift = distance+margin
        delta[2] = lift*(min(1.,weight/.18) if lift>0 else weight)
    return rotated+delta,delta

output = {}
for role in ("reload","reload_empty"):
    times, frames = load(role)
    mats = matrices(frames) @ invbind
    mats = np.linalg.inv(mats[:,root:root+1]) @ mats
    strand = fit_strand(mats,idle,names,dom,verts)
    np.savez_compressed(here/(role+"_strand.npz"), **strand)
    for name,values in strand.items():
        carrier = mats[:,names.index(("New_" if name.startswith("New_") else "")+"PKM_Box")]
        i = names.index(name)
        mats[:,i] = carrier @ as_matrix(values) @ np.linalg.inv(carrier) @ mats[:,i]
    output[role] = {}
    for side,state,window in (("l","Old",(1.17,1.365,2.03,2.32)),("r","New",(4.27,4.50,5.12,5.38))):
        if side == "l" and role == "reload_empty":
            continue
        a,b,c,e = np.array(window) - (.9 if role == "reload_empty" else 0.)
        ids = np.flatnonzero((np.array(times) >= a) & (np.array(times) <= e))
        hand = Surface((slots == d["slots"].index("Skin_Hand")) &
                       np.isin(dom[faces[:,0]],[i for i,n in enumerate(names) if n.endswith("_"+side)]))
        belt = Surface(np.isin(slots,[i for i,n in enumerate(d["slots"]) if n.endswith("__"+state+"Belt")]))
        tipname = ("New_" if state=="New" else "")+"PKM_Belt_00"
        tip = dom[belt.ids] == names.index(tipname)
        pads = [dom[hand.ids] == names.index(digit+"_03_"+side) for digit in ("index","thumb")]
        wrist_id = names.index("hand_"+side)
        wrists = (mats[:,wrist_id]@bind[wrist_id])[:,:3,3]
        obstacle_mats = [np.linalg.inv(mats[:,names.index(("New_" if name=="PKM_Box" and state=="New" else "")+name)])
                         for name in obstacles]
        cached = []
        for i in ids:
            palm = hand.skin(mats[i])
            strip = belt.skin(mats[i])
            center = strip[tip].mean(axis=0)
            low = center[:2] - [8.5,8.5]
            upper = heightfield(strip,belt.faces,low,.09,True)
            cached.append((palm,wrists[i],center,upper,low))
        t = np.asarray(times)[ids]
        blend = ramp(t,a,b)*(1-ramp(t,c,e))
        # Select a single wrist approach for the clip so consecutive frames cannot
        # switch sides. Evaluate the posed wrist, equipment and case surface volumes.
        sample = np.linspace(np.searchsorted(t,b),np.searchsorted(t,c)-1,7).round().astype(int)
        best = (np.inf,None)
        for yaw in (0.,-40.,40.,-80.,80.,-115.,115.,-150.,150.):
            for tilt in (-23.,0.,23.):
                for lateral in (-1.35,0.,1.35):
                    cost = .0015*(abs(yaw)/90+abs(tilt)/30+abs(lateral)/2)
                    for j in sample:
                        palm,delta = place(*cached[j],yaw,tilt,lateral,1.,.16)
                        probes = palm[::9]
                        for field,T in zip(obstacles.values(),obstacle_mats):
                            m = T[ids[j]]
                            cost += field.costs(probes@m[:3,:3].T+m[:3,3])
                        if cost >= best[0]:break
                    if cost < best[0]:best = (cost,(yaw,tilt,lateral))
        yaw,tilt,lateral = best[1]
        corrections = np.asarray([place(*row,yaw,tilt,lateral,w,.16)[1] for row,w in zip(cached,blend)])
        smoothed = gaussian_filter1d(corrections,.85,axis=0,mode="nearest")
        smoothed[:,2] = np.maximum(smoothed[:,2],corrections[:,2]-.025)
        final_delta=np.zeros((len(times),3))
        final_delta[ids]=smoothed
        final_rotation=np.tile([0.,0.,0.,1.],(len(times),1))
        final_rotation[ids]=[Rotation.from_matrix(rotations(yaw*w,tilt*w)).as_quat() for w in blend]
        if side=="l":
            for i,t0 in enumerate(times):
                if not .33<t0<.56:continue
                strip=belt.skin(mats[i]);palm=hand.skin(mats[i])
                low=strip[tip].mean(0)[:2]-[8.5,8.5]
                clearance=np.max(heightfield(strip,belt.faces,low,.09,True)+heightfield(palm,hand.faces,low,.09,False))
                if np.isfinite(clearance):
                    final_delta[i,2]=max(0.,clearance+.18)*ramp(t0,.33,.42)*(1-ramp(t0,.48,.56))
        output[role][side] = {"first":0, "delta_cm":final_delta.round(5).tolist(),
                             "rotation":final_rotation.round(8).tolist()}
        print(role,side,len(ids),flush=True)
(here/"belt_hand_fit.json").write_text(json.dumps(output,separators=(",",":")),encoding="utf8")
