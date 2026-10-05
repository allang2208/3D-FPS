"""Retiming the existing extended bite to 2x with a compact thrust/recoil accent."""
from pathlib import Path
import json, math, bpy
from mathutils import Vector, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV08'
for directory in ('Authoring','Exports','Records'):(OUT/directory).mkdir(parents=True,exist_ok=True)
source=ROOT/'ProductionV07/Authoring/M14_Rigged_Locomotion_v07.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['M14_Rig'];scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['A_M14_Bite_v03']
scene.render.fps=30
samples=[]
for frame in range(58):
    scene.frame_set(frame)
    samples.append({bone.name:(bone.location.copy(),bone.rotation_quaternion.copy(),bone.scale.copy()) for bone in rig.pose.bones})
action=bpy.data.actions.new('A_M14_Bite_v08');action.use_fake_user=True
rig.animation_data.action=action
scene.render.fps=60;scene.frame_start=0;scene.frame_end=57
axes={bone.name:bone.bone.matrix_local.to_3x3().inverted() for bone in rig.pose.bones}

def ease(t):
    t=max(0.,min(1.,t));return t*t*(3.-2.*t)
def pulse(t,start,peak,end):
    return ease((t-start)/(peak-start)) if t<peak else 1.-ease((t-peak)/(end-peak))
def turn(name,axis,angle):
    bone=rig.pose.bones[name]
    bone.rotation_quaternion=Quaternion(axes[name]@Vector(axis),angle)@bone.rotation_quaternion

for frame,sample in enumerate(samples):
    scene.frame_set(frame)
    for bone in rig.pose.bones:
        bone.rotation_mode='QUATERNION'
        bone.location,bone.rotation_quaternion,bone.scale=sample[bone.name]
    t=frame/60.
    thrust=pulse(t,.275,.43,.57)
    recoil=pulse(t,.43,.515,.82)
    # Five extra centimetres at contact; a quick recoil after the hit creates
    # a sharper release without a root teleport or extra damage application.
    rig.pose.bones['maw'].location+=axes['maw']@Vector((0,-.05*thrust+.010*recoil,0))
    for k in range(2,6):
        turn(f'spine_{k:02d}',(1,0,0),.009*thrust-.014*recoil)
    for side in ('L','R'):
        lag=.012 if side=='R' else 0.
        follow=pulse(t,.44+lag,.55+lag,.84+lag)
        turn('sac_'+side,(1,0,0),.030*follow)
    for bone in rig.pose.bones:
        bone.keyframe_insert('location',frame=frame,group=bone.name)
        bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
        bone.keyframe_insert('scale',frame=frame,group=bone.name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
export=OUT/'Exports/A_M14_Bite_v08.fbx'
bpy.ops.export_scene.fbx(filepath=str(export),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
    use_mesh_modifiers=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
# The full mother file retains its original 30 fps action time base. Only this
# new action uses half-frame keys; the exported bite already has 60 Hz samples.
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.co.x*=.5;key.handle_left.x*=.5;key.handle_right.x*=.5
scene.render.fps=30;scene.frame_end=72
rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
scene.frame_set(0)
blend=OUT/'Authoring/M14_Rigged_Bite_v08.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
receipt={'source_blend':str(source),'blend':str(blend),'bite_fbx':str(export),
    'source_action':'A_M14_Bite_v03','action':action.name,'source_duration_seconds':1.9,
    'duration_seconds':.95,'contact_seconds':.43,'export_fps':60,'mother_file_fps':30,'speed_multiplier':2.,
    'extra_maw_thrust_cm':5.,'mouth_reach_cm':125.,'bite_trigger_range_cm':260.,'derived_stop_range_cm':245.,
    'geometry_skin_and_other_actions_preserved':True,'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V08_BITE_AUTHORED',flush=True)
