"""Restore original low/bake pair, preserving the exact M16 receiver interface."""
import bpy,json,math,hashlib,shutil
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];OUT=O/'Final';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
source=P/'SourceAssets/M16StockDonor20261015/Final/SM_M16_tactical_telescopic.fbx'
bpy.ops.import_scene.fbx(filepath=str(source))
old=next(o for o in bpy.context.scene.objects if o.type=='MESH')
native_slot=next(i for i,m in enumerate(old.data.materials) if m.name.startswith('MI_M16_R01_mount_90c3c931dc'))
faces=[f for f in old.data.polygons if f.material_index==native_slot]
used=sorted({v for f in faces for v in f.vertices});index={v:i for i,v in enumerate(used)}
me=bpy.data.meshes.new('M16_PreservedInterface');me.from_pydata([tuple(old.matrix_world@old.data.vertices[v].co) for v in used],[],[tuple(index[v] for v in f.vertices) for f in faces]);me.update()
native=bpy.data.objects.new('M16_PreservedInterface',me);bpy.context.collection.objects.link(native)
native_mat=old.data.materials[native_slot];native_mat.name='M16_InterfaceMetal';me.materials.append(native_mat)
for j,src in enumerate(old.data.uv_layers):
 dst=me.uv_layers.new(name='UVmap_'+str(j));k=0
 for f in faces:
  for li in f.loop_indices:dst.data[k].uv=src.data[li].uv;k+=1
normal_matrix=old.matrix_world.to_3x3().inverted().transposed()
native_normals=[tuple((normal_matrix@old.data.corner_normals[li].vector).normalized()) for f in faces for li in f.loop_indices]
for f in me.polygons:f.use_smooth=True
me.normals_split_custom_set(native_normals)
native_triangles=len(faces)
for ob in list(bpy.context.scene.objects):
 if ob!=native:bpy.data.objects.remove(ob,do_unlink=True)
lib=P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/M4/TacticalStock_Game_Editable.blend'
with bpy.data.libraries.load(str(lib),link=False) as (src,dst):dst.objects=['SM_TacticalTelescopicStock']
body=dst.objects[0]
if body is None:raise RuntimeError('Original M4 matched mesh missing')
bpy.context.collection.objects.link(body);body.hide_set(False);body.hide_render=False
for j,layer in enumerate(body.data.uv_layers):layer.name='UVmap_'+str(j)
body.data.uv_layers.active_index=0;body.data.uv_layers[0].active_render=True
# Material nodes must follow the renamed UV layers too, for the editable source.
for mat in body.data.materials:
 for node in mat.node_tree.nodes:
  if node.type in {'NORMAL_MAP','UVMAP'}:
   node.uv_map='UVmap_1' if node.uv_map=='ReceiverUV1' else 'UVmap_0'
frame=Matrix.Translation(Vector((-.000038,.041045,.0917)))@Matrix.Rotation(math.pi/2,4,'Z')
body.matrix_world=frame@body.matrix_world
body_triangles=sum(len(f.vertices)-2 for f in body.data.polygons)
bpy.ops.object.select_all(action='DESELECT');native.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=native
bpy.ops.object.join();result=bpy.context.object;result.name='SM_M16_Telescopic_MatchedSource'
result.data.uv_layers.active_index=0;result.data.uv_layers[0].active_render=True
# Preserve the complete original normal bake at full strength. Never reuse R2.
normal_src=P/'SourceAssets/StockRefresh20260914/TacticalTelescopic/Textures/Normal_Game.png'
normal_dst=OUT/'T_M16_Telescopic_MatchedNormal.png';shutil.copy2(normal_src,normal_dst)
bpy.ops.file.pack_all();blend=OUT/'M16_Telescopic_MatchedSource_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
fbx=OUT/'SM_M16_Telescopic_MatchedSource.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
report={'original_low_source':str(lib),'mesh_export':str(fbx),'editable':str(blend),'body_triangles':body_triangles,'retained_m16_interface_triangles':native_triangles,'triangles':sum(len(f.vertices)-2 for f in result.data.polygons),'materials':[m.name for m in result.data.materials],'normal_source':str(normal_src),'normal_export':str(normal_dst),'normal_sha256':hashlib.sha256(normal_dst.read_bytes()).hexdigest(),'normal_strength':1,'position_smoothing':False,'normal_recalculation':False,'scope':'M16 only','gameplay_tested':False}
(O/'production.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('MATCHED_SOURCE_EXPORTED',report,flush=True)
