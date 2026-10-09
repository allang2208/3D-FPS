import sys,numpy as np
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O/'pydeps'));import igl
D=np.load(O/'fit_inputs.npz');v=D['vertices'];w=D['weights'];rest=D['rest'];pose=D['idle'];p=np.zeros((len(v),3))
for i in range(len(rest)):
    ids=np.flatnonzero(w[:,i]>1e-6)
    if len(ids):p[ids]+=(v[ids]@(pose[i]@np.linalg.inv(rest[i])).T)[:,:3]*w[ids,i,None]
faces=D['faces'][D['labels']=='gun'].astype(np.int64);p=p.astype(np.float64)
for side in ('l','r'):
    S=np.load(O/('gun_sdf_'+side+'.npz'));grid=np.abs(S['values']);origin=S['origin'];step=S['step']
    xyz=np.indices(grid.shape).reshape(3,-1).T*step+origin;winding=igl.fast_winding_number(p,faces,xyz)
    grid=grid.reshape(-1);grid[np.abs(winding)>.5]*=-1;grid=grid.reshape(S['values'].shape)
    np.savez_compressed(O/('gun_sdf_winding_'+side+'.npz'),values=grid,origin=origin,step=step)
    print('WINDING_SDF',side,'inside',int(sum(np.abs(winding)>.5)),flush=True)
