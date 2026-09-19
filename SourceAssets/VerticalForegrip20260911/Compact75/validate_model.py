import bpy,bmesh,json,hashlib
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'VerticalForegrip_Refined.blend'));o=bpy.data.objects['SM_VerticalForegrip'];bm=bmesh.new();bm.from_mesh(o.data)
d={'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'uv_layers':len(o.data.uv_layers),'materials':[m.name for m in o.data.materials],'images':{}}
for m in o.data.materials:
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   f=Path(bpy.path.abspath(n.image.filepath));d['images'][n.image.name]={'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None}
bm.free();assert d['nonmanifold_edges']==0 and d['zero_area_faces']==0,d
(O/'model_validation.json').write_text(json.dumps(d,indent=2));print(d)
