import bpy,json
from pathlib import Path
from collections import Counter
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90LoaderR24_20261010/Super90_Speedloader_R24.blend'),use_scripts=False)
A=json.loads((S/'Super90QuickMelee20261008/LeftArmR5/author_space.json').read_text())
rig=bpy.data.objects['SK_Super90']; mesh=bpy.data.objects['Super90_V7_M4_BareArmsV6']
C,E=Matrix(A['conversion']['C']),Matrix(A['conversion']['E'])
M=C@E.inverted()@rig.matrix_world.inverted()@mesh.matrix_world
edges=Counter(tuple(sorted(e)) for face in mesh.data.polygons for e in face.edge_keys)
boundary={i for e,c in edges.items() if c==1 for i in e}
vertices=[]
for v in mesh.data.vertices:
 w={mesh.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>.000001}
 if sum(value for n,value in w.items() if n.endswith('_l'))<.8:continue
 vertices.append(dict(index=v.index,position=list(M@v.co),weights=w,boundary=v.index in boundary))
(O/'geometry.json').write_text(json.dumps(dict(source=str(S/'Super90LoaderR24_20261010/Super90_Speedloader_R24.blend'),mesh=mesh.name,vertices=vertices),separators=(',',':')))
print('ARM_AUTHOR_GEOMETRY',len(vertices),sum(v['boundary'] for v in vertices),flush=True)
