"""Retain V11's dense whole-body path; adjust only startup and final settle timing."""
from pathlib import Path
import json
import math
import bpy

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
SOURCE = BASE / 'PounceV11/Delivery'
OUT = BASE / 'PounceV13/Delivery'
OUT.mkdir(parents=True, exist_ok=True)
source_manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'MantisM27_PounceV11.blend'))
scene = bpy.context.scene
scene.render.fps = FPS = 60
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for track in rig.animation_data.nla_tracks:
    track.mute = True
names = [bone.name for bone in rig.data.bones]

# Seconds in the output, seconds in the original V11, endpoint speed.
# Each value drives every bone together. Pose shapes, support trajectories and
# complete arm relationships come from V11, not from V12's sparse reconstruction.
MAPS = {
    'PounceWindup': [(0., 0., .35), (.12, .06, .85), (.26, .26, 1.), (.60, .60, 1.)],
    'PounceLand': [(0., 0., 1.), (.48, .48, 1.), (.60, .65, .95), (.80, .80, .45)],
}

def source_time(role, seconds):
    knots = MAPS[role]
    for left, right in zip(knots, knots[1:]):
        if seconds <= right[0] + 1.e-8:
            start, value0, speed0 = left
            end, value1, speed1 = right
            length = end - start
            t = max(0., min(1., (seconds - start) / length))
            return ((2*t**3 - 3*t*t + 1)*value0 + (t**3 - 2*t*t + t)*length*speed0
                    + (-2*t**3 + 3*t*t)*value1 + (t**3 - t*t)*length*speed1)
    return knots[-1][1]

def activate(action):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]

def dense_source(role):
    activate(bpy.data.actions['A_M27_' + role + '_PounceV11'])
    frames = []
    for index in range(source_manifest['clips'][role]['frames']):
        scene.frame_set(index + 1)
        pose = {}
        for name in names:
            location, rotation, scale = rig.pose.bones[name].matrix_basis.decompose()
            if frames and rotation.dot(frames[-1][name][1]) < 0.:
                rotation.negate()
            pose[name] = (location.copy(), rotation.copy(), scale.copy())
        frames.append(pose)
    return frames

def sample(frames, seconds):
    cursor = min(len(frames) - 1., max(0., seconds * FPS))
    nearest = round(cursor)
    if abs(cursor - nearest) < 1.e-6:
        return frames[nearest]
    low = math.floor(cursor)
    high = min(low + 1, len(frames) - 1)
    alpha = cursor - low
    return {name: (frames[low][name][0].lerp(frames[high][name][0], alpha),
                   frames[low][name][1].slerp(frames[high][name][1], alpha),
                   frames[low][name][2].lerp(frames[high][name][2], alpha)) for name in names}

report = {
    'revision': 'PounceV13', 'status': 'candidate_only', 'source_revision': 'PounceV11',
    'mesh_revision': 'BindingV2', 'fps': FPS, 'clips': {},
    'reused_clips': {'PounceFlight': '/Game/Monsters/MantisM27/PounceV11/Animations/A_M27_PounceFlight_PounceV11'},
    'time_maps_output_source_speed': MAPS,
    'edited_time_ranges_seconds': {'PounceWindup': [0., .26], 'PounceLand': [.48, .80]},
    'design': 'Dense V11 pose path and signed scythe orientation retained; one nonlinear clock for the entire pose; no new body or leg shaping',
    'rejected_revision': 'PounceV12', 'source_license': source_manifest['source_license'],
    'runtime_tested': False, 'offline_validated': False, 'rendered': False, 'native_code_changed': False,
}

# Read both originals before adding any new animation tracks.
sources = {role: dense_source(role) for role in MAPS}
for role, frames in sources.items():
    action = bpy.data.actions.new('A_M27_' + role + '_PounceV13')
    action.use_fake_user = True
    activate(action)
    scene.frame_start, scene.frame_end = 1, len(frames)
    previous = {}
    for index in range(len(frames)):
        pose = sample(frames, source_time(role, index / FPS))
        for name in names:
            location, rotation, scale = pose[name]
            pb = rig.pose.bones[name]
            pb.rotation_mode = 'QUATERNION'
            rotation = rotation.copy()
            if name in previous and previous[name].dot(rotation) < 0.:
                rotation.negate()
            pb.location, pb.rotation_quaternion, pb.scale = location, rotation, scale
            previous[name] = rotation.copy()
            for channel in ['location', 'rotation_quaternion', 'scale']:
                pb.keyframe_insert(channel, frame=index + 1, group=name)
    # Timing is authored above. Linear interpolation of dense export samples
    # prevents Blender from adding an extra Bezier overshoot between samples.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    filename = action.name + '.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT / filename), use_selection=True, object_types={'ARMATURE'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1., axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=True,
        bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0.)
    report['clips'][role] = {**source_manifest['clips'][role], 'file': filename,
        'source': '/Game/Monsters/MantisM27/PounceV11/Animations/A_M27_' + role + '_PounceV11'}
    print('M27_POUNCE_V13_CANDIDATE_EXPORTED ' + role, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MantisM27_PounceV13.blend'))
(OUT / 'motion_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_POUNCE_V13_CANDIDATE_AUTHORED', flush=True)
