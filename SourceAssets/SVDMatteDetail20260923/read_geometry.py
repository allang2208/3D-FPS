"""Read current magazine dimensions and shells for local surface refinement."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVDMagazineFit20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];report={}
for name in ['SM_SVD_Magazine','SM_SVD_MagazineInterior']:
 ob=bpy.data.objects[name];X=(r.matrix_world@r.data.bones['WPN_SOCKET_Magazine'].matrix_local).inverted()@ob.matrix_world
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
 todo=set(bm.verts);islands=[]
 while todo:
  v=todo.pop();group={v};pending=[v]
  while pending:
   for e in pending.pop().link_edges:
    for v in e.verts:
     if v in todo:todo.remove(v);group.add(v);pending.append(v)
  ps=[X@v.co for v in group]
  islands.append({'verts':len(group),'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)]})
 ps=[X@v.co for v in bm.verts]
 report[name]={'verts':len(ob.data.vertices),'faces':len(ob.data.polygons),'matrix':[list(row) for row in X],
 'size':[max(p[i] for p in ps)-min(p[i] for p in ps) for i in range(3)],
 'islands':sorted(islands,key=lambda a:-a['verts']),
 'uvs':[uv.name for uv in ob.data.uv_layers],'materials':[m.name for m in ob.data.materials],
 'custom_normals':ob.data.has_custom_normals,'scale':list(ob.scale)}
 bm.free()
(O/'geometry_inputs.json').write_text(json.dumps(report,indent=2))
print('SVD_MAG_GEOMETRY',json.dumps(report),flush=True)
