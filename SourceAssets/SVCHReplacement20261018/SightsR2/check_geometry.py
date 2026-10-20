"""Scoped source/FBX checks for the requested sight repair."""
import bpy,json
import numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'SVCH_SightsR2_Editable.blend'),load_ui=False)
data={};allv=[];boneweights={};tris=0;source_np=[];source_nn=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 ob.data.calc_loop_triangles();v=np.array([tuple(ob.matrix_world@x.co) for x in ob.data.vertices]);t=np.array([x.vertices[:] for x in ob.data.loop_triangles]);allv.extend(v);tris+=len(t)
 if ob.name.startswith('SVCH_Detailed_'):
  normals=np.array([tuple(n.vector) for n in ob.data.corner_normals]);data[ob.name]={'v':v.tolist(),'t':t.tolist(),'finite':bool(np.isfinite(v).all() and np.isfinite(normals).all()),'zero_normals':int(np.sum(np.linalg.norm(normals,axis=1)<.1)),'bone_names':[g.name for g in ob.vertex_groups]}
  source_np.extend(v[[l.vertex_index for l in ob.data.loops]]);source_nn.extend(normals)
(O/'sight_geometry.json').write_text(json.dumps(data,separators=(',',':')))
np.save(O/'export_expected_vertices.npy',np.asarray(allv));expected_tris=tris
np.savez_compressed(O/'source_corner_normals.npz',p=source_np,n=source_nn)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'SK_SVCH_SightsR2.fbx'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];actual=[];count=0;export_np=[];export_nn=[]
for ob in meshes:
 ob.data.calc_loop_triangles();actual.extend([tuple(ob.matrix_world@x.co) for x in ob.data.vertices]);count+=len(ob.data.loop_triangles)
 matrix=ob.matrix_world.to_3x3().inverted().transposed()
 for poly in ob.data.polygons:
  if ob.data.materials[poly.material_index].name.startswith('SVCH_New_FactorySights'):
   for i in poly.loop_indices:
    export_np.append(tuple(ob.matrix_world@ob.data.vertices[ob.data.loops[i].vertex_index].co));export_nn.append(tuple((matrix@ob.data.corner_normals[i].vector).normalized()))
np.save(O/'export_actual_vertices.npy',np.asarray(actual))
np.savez_compressed(O/'fbx_corner_normals.npz',p=export_np,n=export_nn)
result={'source_triangles':expected_tris,'FBX_triangles':count,'FBX_meshes':len(meshes),'sight_finite':all(r['finite'] for r in data.values()),'zero_sight_normals':sum(r['zero_normals'] for r in data.values()),'sight_bones':{k:v['bone_names'] for k,v in data.items()}}
assert expected_tris==count and result['sight_finite'] and not result['zero_sight_normals']
(O/'source_fbx_check.json').write_text(json.dumps(result,indent=2));print('SOURCE_FBX_CHECK',json.dumps(result),flush=True)
