import bpy,bmesh,numpy as np,json
from pathlib import Path
O=Path(__file__).parent;out={}
for name,filename in [('author','SM_LMG201_H39_BipodBase.fbx'),('saved','After_BipodBase.fbx')]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/filename),use_anim=False);ob=next(q for q in bpy.data.objects if q.type=='MESH');ob.data.transform(ob.matrix_world)
 out[name]={}
 for eps in [0.0000001,0.000001,0.00001]:
  bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=eps);boundary=[e for e in bm.edges if e.is_boundary];out[name][str(eps)]={'open_edges':len(boundary),'bounds':[min(v.co.z for v in bm.verts),max(v.co.z for v in bm.verts)],'edge_samples':[[list(v.co) for v in e.verts] for e in boundary[:8]]};bm.free()
(O/'mount_topology.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
