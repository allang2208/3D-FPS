"""Increase only the existing mouth's outward attack displacement by 50 percent."""
from pathlib import Path
import json, bpy
from mathutils import Vector

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV03'
for directory in ('Authoring','Exports','Records'):(OUT/directory).mkdir(parents=True,exist_ok=True)
source=ROOT/'ProductionV02/Authoring/M14_Rigged_Animated_v02.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['M14_Rig'];scene=bpy.context.scene
original=bpy.data.actions['A_M14_Bite']
action=original.copy();action.name='A_M14_Bite_v03';action.use_fake_user=True
rig.animation_data.action=action
rig.animation_data.action_slot=action.slots[0]
maw=rig.pose.bones['maw']
rest_rotation=maw.bone.matrix_local.to_3x3()
inverse=rest_rotation.inverted();forward=Vector((0,-1,0))
scene.render.fps=30;scene.frame_start=0;scene.frame_end=57
# Sample the source curve as animation authoring input before replacing its mouth keys.
samples=[]
for frame in range(58):
    scene.frame_set(frame)
    delta=rest_rotation@maw.location
    outward=max(0.,delta.dot(forward))
    samples.append((frame,delta.copy(),outward))
for frame,delta,outward in samples:
    maw.location=inverse@(delta+forward*(outward*.5))
    maw.keyframe_insert('location',frame=frame,group='maw')
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    if curve.data_path=='pose.bones["maw"].location':
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
export=OUT/'Exports/A_M14_Bite_v03.fbx'
bpy.ops.export_scene.fbx(filepath=str(export),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
    use_mesh_modifiers=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
rig['bite_outward_displacement_multiplier']=1.5
rig['bite_action']='A_M14_Bite_v03'
rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
scene.frame_set(0)
blend=OUT/'Authoring/M14_Rigged_Animated_v03.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
peak=max(sample[2] for sample in samples)
receipt=dict(source_blend=str(source),blend=str(blend),bite_fbx=str(export),source_action='A_M14_Bite',
    new_action='A_M14_Bite_v03',duration_seconds=1.9,contact_seconds=.86,source_fps=30,
    changed_channel='maw local translation, outward component along armature -Y only',
    outward_displacement_multiplier=1.5,source_peak_outward_cm=peak*100.,new_peak_outward_cm=peak*150.,
    retraction_preserved=True,side_and_height_motion_preserved=True,jaw_opening_preserved=True,
    mesh_and_skin_preserved=True,other_actions_preserved=True,death_revision_preserved='V02',
    hit_location='Existing runtime mouth_socket follows the same maw bone.',tested=False,rendered=False)
(OUT/'Records/authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V03_BITE_AUTHORED',flush=True)
