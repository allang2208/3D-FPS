from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
p=s['idle'];v=deform(p);tree=BVHTree.FromPolygons(v,solids['gun'],all_triangles=True)
for side in ('l','r'):
    subset=[index['hand_'+side]]+[index[n] for n in s['finger_names'][side]]
    selected=np.flatnonzero(weights[:,subset].sum(axis=1)>.995);points=np.asarray([v[i] for i in selected])
    low=points.min(axis=0)-.040;high=points.max(axis=0)+.040;step=.00125
    shape=np.ceil((high-low)/step).astype(int)+1;grid=np.empty(tuple(shape),dtype=np.float32)
    yz=[(j,k) for j in range(shape[1]) for k in range(shape[2])]
    for i in range(shape[0]):
        for j,k in yz:
            at=Vector(low+np.array([i,j,k])*step);near,normal,_,dist=tree.find_nearest(at)
            grid[i,j,k]=-dist if dist<.025 and (at-near).dot(normal)<0 else dist
        if i%25==0:print('SDF',side,i,int(shape[0]),flush=True)
    np.savez_compressed(O/('gun_sdf_'+side+'.npz'),values=grid,origin=low,step=step)
print('GUN_SDFS_SAVED',flush=True)
