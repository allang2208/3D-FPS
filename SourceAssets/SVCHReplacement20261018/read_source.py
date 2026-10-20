"""Record the selected source's authoring coordinates, materials and rigid parts."""
import bpy,json
import numpy as np
from pathlib import Path
O=Path(__file__).parent
S=O/'Download/Extracted/Original/Native/KVInhibitor'
bpy.ops.wm.open_mainfile(filepath=str(S/'KV Inhibitor.blend'),load_ui=False)
report={'objects':[],'materials':[]}
for ob in bpy.data.objects:
 row={'name':ob.name,'type':ob.type,'matrix':list(map(list,ob.matrix_world)),'hidden':ob.hide_render}
 if ob.type=='MESH':
  v=np.array([list(ob.matrix_world@x.co) for x in ob.data.vertices]);ob.data.calc_loop_triangles()
  row.update(vertices=len(v),triangles=len(ob.data.loop_triangles),bounds=[v.min(0).tolist(),v.max(0).tolist()],materials=[m.name if m else None for m in ob.data.materials],uv=[x.name for x in ob.data.uv_layers],custom_normals=ob.data.has_custom_normals,groups={})
  for vg in ob.vertex_groups:
   ids=[x.index for x in ob.data.vertices if any(g.group==vg.index and g.weight>.5 for g in x.groups)]
   if ids:row['groups'][vg.name]={'vertices':len(ids),'bounds':[v[ids].min(0).tolist(),v[ids].max(0).tolist()]}
 elif ob.type=='ARMATURE':
  row['bones']={b.name:{'head':list(ob.matrix_world@b.head_local),'tail':list(ob.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None} for b in ob.data.bones}
 report['objects'].append(row)
for m in bpy.data.materials:
 report['materials'].append({'name':m.name,'nodes':[{'name':n.name,'type':n.bl_idname,'image':n.image.filepath if n.type=='TEX_IMAGE' and n.image else None} for n in m.node_tree.nodes] if m.use_nodes else [],'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.use_nodes else []})
(O/'source_inventory.json').write_text(json.dumps(report,indent=2))
print('SOURCE_INVENTORY_SAVED',[(r['name'],r.get('triangles'),r.get('bounds')) for r in report['objects']])
