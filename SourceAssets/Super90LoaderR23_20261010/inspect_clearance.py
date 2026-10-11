import json
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from repair_core import O,g,rest,ri,rack_time
mesh=g['meshes']['Super90_V7_M4_BareArmsV6'];weights=mesh['weights'];v=np.c_[mesh['positions'],np.ones(len(mesh['positions']))]
digits=[n for n in rest if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
ids=np.array([i for i,w in enumerate(weights) if sum(a for n,a in w.items() if n in digits or n=='hand_l')>.98])
groups={}
for n in rest:
    ix=np.array([j for j,i in enumerate(ids) if weights[i].get(n,0)>1e-5])
    if len(ix):groups[n]=(ix,np.array([weights[ids[j]][n] for j in ix]),v[ids[ix]]@ri[n].T)
grid=np.load(O/'receiver_surface.npz');lookup=RegularGridInterpolator((grid['ys'],grid['zs']),grid['surface'],bounds_error=False,fill_value=-1.)
def extent(p):
    gi=np.linalg.inv(p['WPN_root']@ri['WPN_root']);points=np.zeros((len(ids),3))
    for n,(ix,w,local) in groups.items():points[ix]+=(local@(gi@p[n]).T)[:,:3]*w[:,None]
    return points,lookup(points[:,1:3])-points[:,0]
if __name__=='__main__':
    data=json.loads((O/'repaired_poses.json').read_text())
    for branch in ('empty','cycle'):
        print(branch)
        for f,raw in enumerate(data[branch]):
            t=rack_time(branch,f)
            if not 18<=t<=60:continue
            p={n:np.array(m) for n,m in raw.items()};points,d=extent(p);j=np.argmax(d)
            print(f,round(t,1),round(max(0,d[j])*1000,2),list(weights[ids[j]].items()),points[j].round(3))
