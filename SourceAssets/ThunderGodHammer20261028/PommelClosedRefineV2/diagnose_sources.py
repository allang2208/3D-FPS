import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;R=P.parent
result={}
for kind,src in [('LeiXi','LeiXiPommelV1/LeiXiPommelV1_Editable.blend'),('ZhenTing','ZhenTingPommelV1/ZhenTingPommelV1_Editable.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(R/src));o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update()
 boundary=[e for e in bm.edges if e.is_boundary];bad=[e for e in bm.edges if len(e.link_faces)>2]
 tree=BVHTree.FromBMesh(bm);rays=[]
 import math
 for z in [-.0255,-.031,-.040,-.050,-.060,-.068,-.074]:
  for i in range(16):
   a=i*math.pi/8;d=Vector((math.cos(a),math.sin(a),0));start=Vector((-.0006,-.001,z))+d*.07
   p,n,f,dist=tree.ray_cast(start,-d,.14)
   if p is None or n.dot(d)<0:rays.append({'z':z,'angle':i*22.5,'missing':p is None,'backface':p is not None and n.dot(d)<0})
 result[kind]={'open_edges_after_position_weld':len(boundary),'multi_face_edges':len(bad),'open_edge_z_extents':[min(v.co.z for e in boundary for v in e.verts),max(v.co.z for e in boundary for v in e.verts)] if boundary else [],'backface_or_missing_first_surfaces':rays}
 bm.free()
(P/'source_diagnosis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
