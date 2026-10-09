import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'BenelliM4_Original_Editable.blend'))
src=bpy.data.objects['benelli_m4_TTI_Benelli_M4_0'];original=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(S/'Original/glb.glb'))
out={}
for o in [src]+[x for x in bpy.data.objects if x not in original and x.type=='MESH']:
    me=o.data
    out[o.name]={'matrix':list(map(list,o.matrix_world)),'bbox':list(map(list,o.bound_box)),
       'verts':[[*v.co] for v in me.vertices],
       'triangles':[list(p.vertices) for p in me.polygons],
       'uv':[[*x.uv] for x in me.uv_layers[0].data],
       'normals':[[*n.vector] for n in me.corner_normals],
       'materials':[m.name for m in me.materials]}
(O/'author_basis.json').write_text(json.dumps(out));print([(k,len(v['verts']),v['materials']) for k,v in out.items()])
