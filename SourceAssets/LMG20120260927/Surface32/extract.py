"""Read the fitted source for in-place vertex/corner refinement; no renders."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;(O/'Work').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Install30/LMG201_R30_NativeFit.blend'),use_scripts=False)
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local
parts={};records=[]
for ob in list(bpy.context.scene.objects):
 if ob.type!='MESH' or ob.hide_render:continue
 me=ob.data;me.calc_loop_triangles();mat=root.inverted()@ob.matrix_world
 vertices=np.array([mat@v.co for v in me.vertices]); faces=np.array([t.vertices[:] for t in me.loop_triangles]);loops=np.array([t.loops[:] for t in me.loop_triangles])
 normals=np.array([mat.to_3x3().inverted().transposed()@n.vector for n in me.corner_normals]);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
 uv=np.array([x.uv[:] for x in me.uv_layers[0].data]) if me.uv_layers else np.zeros((len(me.loops),2))
 key=ob.name;np.savez_compressed(O/'Work'/(key+'.npz'),vertices=vertices,faces=faces,loops=loops,normals=normals,uv=uv,material_ids=np.array([t.material_index for t in me.loop_triangles]))
 records.append({'object':key,'vertices':len(vertices),'triangles':len(faces),'bounds_m':[vertices.min(0).tolist(),vertices.max(0).tolist()],'matrix':np.array(mat).tolist(),'materials':[m.name for m in me.materials]})
(O/'source.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2),flush=True)
