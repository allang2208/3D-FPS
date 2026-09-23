"""Read only production geometry and existing grouped grasp inputs; no rendering."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDHandRepair20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SM_SVD_Magazine']
rest=r.data.bones['WPN_SOCKET_Magazine'].matrix_local
X=(r.matrix_world@rest).inverted()@ob.matrix_world
points=[X@v.co for v in ob.data.vertices]
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
edges={e for e in bm.edges if e.is_boundary};loops=[]
while edges:
 e=edges.pop();vs=set(e.verts);es={e};todo=list(e.verts)
 while todo:
  v=todo.pop()
  for e in v.link_edges:
   if e in edges:
    edges.remove(e);es.add(e)
    for w in e.verts:
     if w not in vs:vs.add(w);todo.append(w)
 pp=[X@v.co for v in vs]
 loops.append({'edges':len(es),'min':[min(v[i] for v in pp) for i in range(3)],'max':[max(v[i] for v in pp) for i in range(3)],'points':[list(v) for v in pp]})
bm.free()
d={'space':'magazine bone rest, metres','transform':[list(x) for x in X],'object_matrix':[list(x) for x in ob.matrix_world],
 'magazine':{'vertices':[list(p) for p in points],'faces':[list(p.vertices) for p in ob.data.polygons]},
 'boundaries':loops,'materials':[m.name for m in ob.data.materials],'groups':[g.name for g in ob.vertex_groups],
 'modifiers':[(m.name,m.type) for m in ob.modifiers],'bones':{b.name:[list(x) for x in b.matrix_local] for b in r.data.bones}}
(O/'geometry_input.json').write_text(json.dumps(d))
print('SVD_MAG_INPUT',len(points),len(ob.data.polygons),d['materials'],flush=True)
print('SVD_MAG_BOUNDS',[(min(p[i] for p in points),max(p[i] for p in points)) for i in range(3)],flush=True)
for l in loops:print('SVD_MAG_BOUNDARY',{k:v for k,v in l.items() if k!='points'},flush=True)
