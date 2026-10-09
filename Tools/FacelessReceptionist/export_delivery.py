"""Emit a single render mesh for UE while retaining independent editable garments."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
# The Nurse FBX's armature object represents its real UE root bone. Naming it
# Armature would make Unreal strip that root and expose five root branches.
rig.name='root';rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
allmeshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
body=bpy.data.objects['Receptionist_CompleteBody']
def select(objects):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=rig
def fbx(file,meshes):
 select([rig]+meshes)
 bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/file),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE')
select([rig]+allmeshes)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_V01.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True)
select([rig]+[o for o in allmeshes if o!=body])
bpy.ops.export_scene.gltf(filepath=str(ROOT/'Delivery/FacelessReceptionist_Clothing_V01.glb'),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_all_influences=True)
fbx('SK_FacelessReceptionist_Body_V01.fbx',[body])
copies=[]
for o in allmeshes:
 d=o.copy();d.data=o.data.copy();bpy.context.collection.objects.link(d);copies.append(d)
bpy.ops.object.select_all(action='DESELECT')
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=copies[allmeshes.index(body)]
bpy.ops.object.join();merged=bpy.context.object;merged.name='Receptionist_RenderMesh'
fbx('SK_FacelessReceptionist_V01.fbx',[merged])
print('RECEPTIONIST_SINGLE_ROOT_EXPORT_SAVED',flush=True)
