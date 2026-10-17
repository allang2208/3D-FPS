import bpy,json,collections,numpy as np
from pathlib import Path
O=Path(__file__).parent;P=O.parent
R={}
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(P/'Meshes'/('SM_M870_'+key+'_Editable.blend')),link=False) as (_,d):d.objects=['SM_M870_'+key]
 o=d.objects[0];bpy.context.collection.objects.link(o);m=o.data;m.calc_loop_triangles();m.calc_tangents(uvmap=m.uv_layers[0].name)
 ts=np.array([list(l.tangent) for l in m.loops]);ns=np.array([list(n.vector) for n in m.corner_normals]);areas=[t.area for t in m.loop_triangles]
 mats={}
 for f in m.polygons:
  row=mats.setdefault(m.materials[f.material_index].name,{'faces':0,'uv_zero':0,'zero_tangent':0,'zero_normal':0,'min_area':1.})
  row['faces']+=1;row['min_area']=min(row['min_area'],f.area)
  q=[m.uv_layers[0].data[i].uv for i in f.loop_indices];row['uv_zero']+=abs((q[1]-q[0]).cross(q[2]-q[0]))<1e-10
  row['zero_tangent']+=sum(float(ts[i]@ts[i])<.1 for i in f.loop_indices);row['zero_normal']+=sum(float(ns[i]@ns[i])<.1 for i in f.loop_indices)
 R[key]={'vertices':len(m.vertices),'triangles':len(m.loop_triangles),'uv_layers':[l.name for l in m.uv_layers],'materials':mats}
 print(key,json.dumps(R[key]),flush=True)
(O/'diagnosis.json').write_text(json.dumps(R,indent=2))
