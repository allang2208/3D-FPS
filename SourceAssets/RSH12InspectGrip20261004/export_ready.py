import sys,json
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
from held_grip import HeldGrip
rig,D,profile,meta=load();solver=HeldGrip(rig,D,profile,meta);names=list(rig.data.bones.keys());parents=[names.index(D['parents'][n]) if D['parents'][n] in names else -1 for n in names]
p=pose(rig,D,profile,'inspect',D['clips']['inspect']['samples'][72]);solver.apply(p);skin=Skin(rig,'r');canon=canonical_pose(p,meta)
np.savez_compressed(O/'input_ready_r_idle.npz',world=np.array([canon@p[n] for n in names]),local=np.array([p[D['parents'][n]].inverted()@p[n] if D['parents'][n] in p else p[n] for n in names]),names=names,parents=parents,coords=skin.coords,weights=skin.weights,bound=skin.bound,used=[names.index(n) for n in skin.used],labels=skin.labels)
print('READY_INPUT_SAVED',flush=True)
