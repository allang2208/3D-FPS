import bpy,bmesh
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ReceiverGrip08.blend'))
ob=bpy.data.objects['phantom_reargrip_ContinuousGrip08'];bm=bmesh.new();bm.from_mesh(ob.data)
print('FAULTS',[(len(e.link_faces),[list(v.co) for v in e.verts]) for e in bm.edges if not e.is_manifold],flush=True)
todo=set(bm.verts);parts=[]
while todo:
    verts={todo.pop()};stack=list(verts)
    while stack:
        v=stack.pop()
        for e in v.link_edges:
            other=e.other_vert(v)
            if other in todo:todo.remove(other);verts.add(other);stack.append(other)
    parts.append(verts)
print('COMPONENTS',sorted([len(p) for p in parts],reverse=True),flush=True)
