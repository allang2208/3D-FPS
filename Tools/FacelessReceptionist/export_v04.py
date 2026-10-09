import bpy,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V04.blend'))
rig=bpy.data.objects['root'];body=bpy.data.objects['Receptionist_CompleteBody']
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
bpy.context.scene.frame_set(0)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
display=bpy.data.objects['Receptionist_OutfitBody']
allmeshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body];keynames=sorted({k.name for o in allmeshes if o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name!='Basis'})
for o in allmeshes:
 if o.data.shape_keys:
  for k in o.data.shape_keys.key_blocks:k.value=0
def select(objects,active=None):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=active or rig
def fbx(filename,meshes):
 select([rig]+meshes)
 bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/filename),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
def merged(objects,name):
 copies=[]
 for o in objects:
  d=o.copy();d.data=o.data.copy();bpy.context.collection.objects.link(d);copies.append(d)
 active=copies[0]
 if not active.data.shape_keys:active.shape_key_add(name='Basis')
 for k in keynames:
  if k not in active.data.shape_keys.key_blocks:active.shape_key_add(name=k)
 select(copies,active);bpy.ops.object.join();result=bpy.context.object;result.name=name
 actual={k.name for k in result.data.shape_keys.key_blocks if k.name!='Basis'}
 if actual!=set(keynames):raise RuntimeError('Merge lost corrective shapes')
 return result
select([rig]+allmeshes)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_V04.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True,export_morph=True)
clothing=[o for o in allmeshes if o!=display]
select([rig]+clothing)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_Clothing_V04.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True,export_morph=True)
body.hide_set(False);fbx('SK_FacelessReceptionist_Body_V04.fbx',[body]);body.hide_set(True)
cloth=merged(clothing,'Receptionist_Clothing_V04');fbx('SK_FacelessReceptionist_Clothing_V04.fbx',[cloth]);bpy.data.objects.remove(cloth,do_unlink=True)
whole=merged([display]+clothing,'Receptionist_RenderMesh_V04');fbx('SK_FacelessReceptionist_V04.fbx',[whole])
report={'morph_names':keynames,'morph_count':len(keynames),'body_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'full_triangles':sum(len(p.vertices)-2 for p in whole.data.polygons),'clothing_parts':len(clothing),'bone_count':len(rig.data.bones)+1}
(ROOT/'export_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V04_EXPORT_COMPLETE',json.dumps(report),flush=True)
