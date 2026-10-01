"""Export the authored rig, materials and sixteen actions. No tests or renders."""
import bpy
import json
import shutil
from pathlib import Path
from mathutils import Matrix

AUTHOR=Path(__file__).resolve().parent
ROOT=AUTHOR.parent
OUT=ROOT/'DeliveryV1';OUT.mkdir(exist_ok=True)
ANIMS=OUT/'Animations';ANIMS.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(AUTHOR/'HundredEyedSlag_RigAndAnimations.blend'))
receipt=json.loads((AUTHOR/'authoring_receipt.json').read_text(encoding='utf-8'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1
textures=OUT/'Textures';textures.mkdir(exist_ok=True)
for name in receipt['textures']:shutil.copy2(AUTHOR/'Textures'/name,textures/name)

fbx_common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
                bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
                bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
                bake_anim_step=1.0,bake_anim_simplify_factor=0.0,
                axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',use_custom_props=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
model=OUT/'SK_HundredEyedSlag_V1.fbx'
print('EXPORT: bound model FBX',flush=True)
bpy.ops.export_scene.fbx(filepath=str(model),object_types={'ARMATURE','MESH'},
                         bake_anim=False,use_mesh_modifiers=False,
                         mesh_smooth_type='OFF',path_mode='COPY',embed_textures=True,**fbx_common)
files=[{'file':model.name,'bytes':model.stat().st_size,'kind':'bound_model'}]
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for contract in receipt['actions']:
    action=bpy.data.actions[contract['action']]
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_end=contract['end_frame_inclusive'];scene.frame_set(1)
    file=OUT/contract['file']
    print('EXPORT: '+contract['name'],flush=True)
    bpy.ops.export_scene.fbx(filepath=str(file),object_types={'ARMATURE'},
                             bake_anim=True,path_mode='AUTO',embed_textures=False,**fbx_common)
    files.append({'file':contract['file'],'bytes':file.stat().st_size,'kind':'skeletal_animation'})

rig.animation_data.action=bpy.data.actions['A_HundredEyedSlag_Idle']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_end=91;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=OUT/'HundredEyedSlag_RigAndAnimations.glb'
gltf_options=dict(filepath=str(glb),export_format='GLB',use_selection=True,
                  export_animations=True,export_skins=True,export_all_influences=False,
                  export_def_bones=False,export_yup=True,export_normals=True,
                  export_tangents=True,export_morph=False,export_materials='EXPORT',
                  export_extras=True)
# Select the installed exporter's action mode from its native API definition.
properties=bpy.ops.export_scene.gltf.get_rna_type().properties
if 'export_animation_mode' in properties:gltf_options['export_animation_mode']='ACTIONS'
if 'export_frame_range' in properties:gltf_options['export_frame_range']=False
if 'export_force_sampling' in properties:gltf_options['export_force_sampling']=True
if 'export_optimize_animation_size' in properties:gltf_options['export_optimize_animation_size']=False
print('EXPORT: animated GLB with PBR',flush=True)
bpy.ops.export_scene.gltf(**gltf_options)
files.append({'file':glb.name,'bytes':glb.stat().st_size,'kind':'bound_animated_glb'})
blend=OUT/'HundredEyedSlag_RigAndAnimations.blend'
# Save with paths relative to this delivery directory and already packed maps.
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
files.append({'file':blend.name,'bytes':blend.stat().st_size,'kind':'editable_source'})

contract={'fps':30,'frame_index_origin':1,'frame_time_formula':'(frame - 1) / 30',
          'forward_axis_blender':'+X','up_axis_blender':'+Z',
          'default_root_motion':False,'root_motion_action':'SpecialCharge_RM',
          'sockets':['ash_origin','attack_origin'],'actions':receipt['actions'],
          'vfx_authored':False,'damage_logic_authored':False,'ue_imported':False,'tested':False}
(OUT/'animation_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
receipt['stage']='bound_model_and_16_original_animations_exported'
receipt['files']=files;receipt['ue_imported']=False;receipt['animation_tested']=False
(OUT/'delivery_manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('DELIVERY_COMPLETE '+json.dumps({'bones':receipt['bones'],
      'deform_bones':receipt['deform_bones'],'actions':len(receipt['actions']),
      'files':len(files),'ue_imported':False,'tested':False}),flush=True)
