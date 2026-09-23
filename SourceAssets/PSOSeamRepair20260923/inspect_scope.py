"""Inspect only the reported PSO body seams in the current SVD author source."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST';bpy.context.view_layer.update()
report={}
for name in ['SM_SVD_ScopeBody','SM_SVD_ScopeMount','SM_SVD_ScopeLens']:
 ob=bpy.data.objects[name];X=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted()@ob.matrix_world
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
 bm.verts.index_update();todo=set(bm.verts);islands=[]
 while todo:
  v=todo.pop();group={v};pending=[v]
  while pending:
   for e in pending.pop().link_edges:
    for v in e.verts:
     if v in todo:todo.remove(v);group.add(v);pending.append(v)
  ps=[X@v.co for v in group]
  islands.append({'verts':len(group),'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)]})
 edges={e for e in bm.edges if e.is_boundary};loops=[]
 while edges:
  e=edges.pop();group={e};vs=set(e.verts);pending=list(e.verts)
  while pending:
   for e in pending.pop().link_edges:
    if e in edges:
     edges.remove(e);group.add(e)
     for v in e.verts:
      if v not in vs:vs.add(v);pending.append(v)
  ps=[X@v.co for v in vs]
  loops.append({'edges':len(group),'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)],
   'center':list(sum(ps,Vector())/len(ps)),'points':[list(p) for p in ps],
   'closed':all(sum(e in group for e in v.link_edges)==2 for v in vs)})
 ps=[X@v.co for v in bm.verts]
 entry={'vertices':len(ob.data.vertices),'faces':len(ob.data.polygons),'matrix':[list(row) for row in X],
 'uvs':[uv.name for uv in ob.data.uv_layers],'materials':[m.name for m in ob.data.materials],
 'islands':sorted(islands,key=lambda a:-a['verts']),'boundaries':sorted(loops,key=lambda l:-l['edges'])}
 report[name]=entry
 print('PSO_INPUT',name,entry['vertices'],entry['faces'],flush=True)
 for i,loop in enumerate(entry['boundaries']):print('PSO_BOUNDARY',i,{k:v for k,v in loop.items() if k!='points'},flush=True)
 bm.free()
(O/'scope_geometry.json').write_text(json.dumps(report,indent=2))
