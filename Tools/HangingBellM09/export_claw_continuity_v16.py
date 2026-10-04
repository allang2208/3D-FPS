"""Package the continuous small arms and redesigned claw on the existing M09 rig."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ArmContinuityV16'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Authoring/M09_ContinuousArms_V16.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
with bpy.data.libraries.load(str(ROOT/'CrownClawV15/Authoring/M09_CrownClaw_V15.blend')) as (src,dst):dst.actions=['A_M09_CrownClaw_V15']
action=dst.actions[0];action.name='A_M09_CrownClaw_V16'
rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
rig.data.pose_position='POSE';scene.render.fps=60;scene.render.fps_base=1.;scene.frame_start=1;scene.frame_end=67;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
options=dict(use_selection=True,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL')
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/A_M09_CrownClaw_V16.fbx'),object_types={'ARMATURE'},
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,**options)
rig.data.pose_position='REST'
for ob in scene.objects:
    if ob.type=='MESH' and ob.parent==rig:ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/M09_ContinuousArms_V16.fbx'),object_types={'ARMATURE','MESH'},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='FACE',**options)
rig.data.pose_position='POSE';scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Claw_Continuous_V16.blend'),compress=True)
(OUT/'Records/export_saved.json').write_text(json.dumps({'complete':True,'duration':1.1,'contact':[.35,.55],
    'animation_source':'CrownClawV15 reconstructed path, same runtime contract','geometry':'ArmContinuityV16 wrist union and front socket repair',
    'skeleton_changed':False,'game_tested':False,'physics_asset_changed':False},indent=2),encoding='utf8')
print('M09_CONTINUOUS_CLAW_V16_EXPORTED',flush=True)
