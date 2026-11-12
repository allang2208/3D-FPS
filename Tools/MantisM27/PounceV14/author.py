"""V11 pounce flight with a longer coil and a more concentrated scythe release."""
from pathlib import Path
import json
import math
import bpy

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
SOURCE = BASE / 'PounceV11/Delivery'
OUT = BASE / 'PounceV14/Delivery'
OUT.mkdir(parents=True, exist_ok=True)
source_manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'MantisM27_PounceV11.blend'))
scene = bpy.context.scene
scene.render.fps = FPS = 60
rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
for track in rig.animation_data.nla_tracks:
    track.mute = True
names = [bone.name for bone in rig.data.bones]
ROLE = 'PounceFlight'

# Output seconds, V11 source seconds, source-time speed at the knot.
# Keep the launch unchanged; let the existing overhead pose build slightly
# longer, concentrate the existing cut, then retain its follow-through endpoint.
# One time map carries pelvis/spine/shoulders/elbows/wrists/legs together.
TIME_MAP = [(0., 0., 1.), (.25, .25, 1.), (.42, .34, .65),
            (.59, .60, 1.15), (.65, .65, 1.)]

def source_time(seconds):
    for left, right in zip(TIME_MAP, TIME_MAP[1:]):
        if seconds <= right[0] + 1.e-8:
            start, value0, speed0 = left
            end, value1, speed1 = right
            length = end - start
            t = max(0., min(1., (seconds - start) / length))
            return ((2*t**3 - 3*t*t + 1)*value0 + (t**3 - 2*t*t + t)*length*speed0
                    + (-2*t**3 + 3*t*t)*value1 + (t**3 - t*t)*length*speed1)
    return TIME_MAP[-1][1]

def activate(action):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]

activate(bpy.data.actions['A_M27_PounceFlight_PounceV11'])
frames = []
for index in range(source_manifest['clips'][ROLE]['frames']):
    scene.frame_set(index + 1)
    pose = {}
    for name in names:
        location, rotation, scale = rig.pose.bones[name].matrix_basis.decompose()
        if frames and rotation.dot(frames[-1][name][1]) < 0.:
            rotation.negate()
        pose[name] = (location.copy(), rotation.copy(), scale.copy())
    frames.append(pose)

def sample(seconds):
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

action = bpy.data.actions.new('A_M27_PounceFlight_PounceV14')
action.use_fake_user = True
activate(action)
scene.frame_start, scene.frame_end = 1, len(frames)
previous = {}
for index in range(len(frames)):
    pose = sample(source_time(index / FPS))
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
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MantisM27_PounceV14.blend'))
report = {
    'revision': 'PounceV14', 'status': 'candidate_only', 'source_revision': 'PounceV11',
    'user_feedback': 'V12 reduced the speed and force of the paired scythe strike',
    'mesh_revision': 'BindingV2', 'fps': FPS,
    'clips': {ROLE: {**source_manifest['clips'][ROLE], 'file': filename,
        'source': '/Game/Monsters/MantisM27/PounceV11/Animations/A_M27_PounceFlight_PounceV11'}},
    'reused_clips': {role: '/Game/Monsters/MantisM27/PounceV11/Animations/A_M27_' + role + '_PounceV11'
        for role in ['PounceWindup', 'PounceLand']},
    'time_map_output_source_speed': TIME_MAP, 'edited_time_range_seconds': [.25, .65],
    'release_source_range_seconds': [.34, .60], 'release_output_range_seconds': [.42, .59],
    'design': 'V11 dense complete pose and signed scythe path; continuous coil, concentrated downstroke and existing braking; same clock for all bones',
    'source_license': source_manifest['source_license'], 'rejected_revision': 'PounceV12',
    'formal_revision_retained': 'PounceV11', 'runtime_tested': False,
    'offline_validated': False, 'rendered': False, 'native_code_changed': False,
}
(OUT / 'motion_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_POUNCE_V14_STRIKE_CANDIDATE_AUTHORED', flush=True)
