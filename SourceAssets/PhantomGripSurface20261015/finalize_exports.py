import bpy,bmesh,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'production.json').read_text());R={}
for key,row in C['assets'].items():
 bpy.ops.wm.open_mainfile(filepath=row['blend']);bpy.context.preferences.filepaths.save_version=0;ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;fixed=0;removed=0
 if key=='LMG201':
  normals=[tuple((ob.matrix_world.to_3x3().inverted().transposed()@n.vector).normalized()) for n in me.corner_normals];me.transform(ob.matrix_world);ob.parent=None;from mathutils import Matrix;ob.matrix_world=Matrix.Identity(4);me.normals_split_custom_set(normals)
 if key!='LMG201':
  attr=me.attributes.new('AuthoredSurfaceNormal','FLOAT_VECTOR','CORNER');ns=np.asarray([tuple(n.vector) for n in me.corner_normals]);bad=np.linalg.norm(ns,axis=1)<.9
  for f in me.polygons:
   for li in f.loop_indices:
    if bad[li]:ns[li]=f.normal if f.normal.length>.9 else (0,0,1);fixed+=1
  attr.data.foreach_set('vector',ns.astype(np.float32).ravel());bm=bmesh.new();bm.from_mesh(me);tiny=[f for f in bm.faces if f.material_index==row['body_slot'] and f.calc_area()<1e-14];removed=len(tiny)
  if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES')
  bm.to_mesh(me);bm.free();me.normals_split_custom_set([tuple(n.vector) for n in me.attributes['AuthoredSurfaceNormal'].data]);me.attributes.remove(me.attributes['AuthoredSurfaceNormal'])
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.fbx(filepath=row['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.ops.wm.save_as_mainfile(filepath=row['blend']);row['triangles']=len(me.polygons);row['removed_zero_area_body_faces']=removed;row['repaired_zero_corner_normals']=fixed;R[key]={'removed':removed,'normals':fixed};print('PHANTOM_FINAL_EXPORT',key,removed,fixed,flush=True)
 (O/'production.json').write_text(json.dumps(C,indent=2))
(O/'export_cleanup.json').write_text(json.dumps(R,indent=2))
