"""Build a local grip SDF and exact LBS inputs for contact authoring."""
import sys,json
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
side=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'single'
rig,D,profile,meta=load(side)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
names=list(rest);parents=[names.index(D['parents'][n]) if D['parents'][n] in names else -1 for n in names]
for hand in (('r','l') if side=='single' else (side,)):
    skin=Skin(rig,hand)
    for kind in ('idle','aim','inspect'):
        if kind not in D['clips']:continue
        sample=min(D['clips'][kind]['samples'],key=lambda s:abs(s['time']-(1.2 if kind=='inspect' else 0)))
        p=pose(rig,D,profile,kind,sample);canon=canonical_pose(p,meta)
        world=np.array([canon@p[n] for n in names]);local=np.array([p[D['parents'][n]].inverted()@p[n] if D['parents'][n] in p else p[n] for n in names])
        np.savez_compressed(O/(f'input_{side}_{hand}_{kind}.npz'),world=world,local=local,names=names,parents=parents,
            coords=skin.coords,weights=skin.weights,bound=skin.bound,used=[names.index(n) for n in skin.used],labels=skin.labels)
        print('FIT_INPUT',side,hand,kind,flush=True)
if not (O/'grip_sdf_closed.npz').exists():
    tree=grip_trees()[0][1]
    axes=[np.arange(-.055,.056,.0015),np.arange(.065,.231,.0015),np.arange(-.115,.061,.0015)]
    field=np.empty(tuple(len(a) for a in axes),dtype=np.float32)
    for i,x in enumerate(axes[0]):
        for j,y in enumerate(axes[1]):
            for k,z in enumerate(axes[2]):field[i,j,k]=signed(tree,(x,y,z))
        if i%12==0:print('SDF_SLICE',i,len(axes[0]),flush=True)
    np.savez_compressed(O/'grip_sdf_closed.npz',x=axes[0],y=axes[1],z=axes[2],field=field)
