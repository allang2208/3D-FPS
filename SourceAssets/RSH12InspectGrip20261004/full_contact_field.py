import sys,json
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
trees=[]
for name in ('9_l','7_l','11_l'):
    part=json.loads((O/('solid_'+name+'.json')).read_text());trees.append(BVHTree.FromPolygons([Vector(v) for v in part['verts']],part['faces']))
source=np.load(O/'grip_sdf_closed.npz');axes=[source[k] for k in ('x','y','z')];field=source['field'].copy()
for i,x in enumerate(axes[0]):
    for j,y in enumerate(axes[1]):
        for k,z in enumerate(axes[2]):field[i,j,k]=min(field[i,j,k],*(signed(tree,(x,y,z)) for tree in trees[1:]))
np.savez_compressed(O/'full_sdf.npz',x=axes[0],y=axes[1],z=axes[2],field=field)
print('FULL_CONTACT_FIELD_SAVED',flush=True)
