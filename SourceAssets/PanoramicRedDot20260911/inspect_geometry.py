import bpy,bmesh,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob('*textured_master*.glb'))))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
remaining=set(bm.verts);islands=[]
while remaining:
 seed=remaining.pop();part={seed};todo=[seed]
 while todo:
  v=todo.pop()
  for edge in v.link_edges:
   w=edge.other_vert(v)
   if w in remaining:remaining.remove(w);part.add(w);todo.append(w)
 faces={f for v in part for f in v.link_faces}
 islands.append({'verts':len(part),'faces':len(faces),'lo':[min(v.co[i] for v in part) for i in range(3)],'hi':[max(v.co[i] for v in part) for i in range(3)]})
islands.sort(key=lambda x:-x['faces'])
(P/'islands.json').write_text(json.dumps(islands,indent=2))
print(json.dumps(islands[:15]))
