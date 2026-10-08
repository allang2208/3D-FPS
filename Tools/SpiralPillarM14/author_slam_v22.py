"""Retime the supported V13 slam, preserving its contact pose and rigid hardware."""
from pathlib import Path
import json
import math
import bpy

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004'
OUT = ROOT / 'ProductionV22'
PLAN = json.loads(Path(__file__).with_name('slam_v22.json').read_text(encoding='utf8'))
for directory in ('Authoring', 'Exports', 'Records'):
    (OUT / directory).mkdir(parents=True, exist_ok=True)
# Continue the latest mother so the preceding V21 bite remains editable too.
source = ROOT / 'ProductionV21/Authoring/M14_StagedBite_v21.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = bpy.data.objects['M14_Rig']
original = bpy.data.actions[PLAN['source_action']]
rig.animation_data.action = original
rig.animation_data.action_slot = original.slots[0]
scene.render.fps = 30

def ease(q):
    q = max(0., min(1., q))
    return q * q * (3. - 2. * q)

def burst(q):
    q = max(0., min(1., q))
    return q ** 3 * (4. - 3. * q)

def source_time(t):
    wind, hit = PLAN['anticipation_end_seconds'], PLAN['contact_seconds']
    if t <= wind:
        return .8 * t / wind
    if t <= hit:
        return .8 + .4 * burst((t - wind) / (hit - wind))
    # Two-frame impact hold, a fast recoil, then progressively settled recovery.
    keys = [(hit, 1.2), (hit + 2. / PLAN['export_fps'], 1.2),
            (PLAN['rebound_peak_seconds'], 1.3), (PLAN['recovery_start_seconds'], 1.48),
            (PLAN['duration_seconds'], 3.2)]
    for (ta, va), (tb, vb) in zip(keys, keys[1:]):
        if t <= tb:
            return va + (vb - va) * ease((t - ta) / (tb - ta))
    return keys[-1][1]

fps = PLAN['export_fps']
frames = round(PLAN['duration_seconds'] * fps)
samples = []
for frame in range(frames + 1):
    at = source_time(frame / fps) * 30.
    scene.frame_set(math.floor(at), subframe=at % 1.)
    samples.append({pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy())
                    for pb in rig.pose.bones})
action = bpy.data.actions.new(PLAN['action'])
action.use_fake_user = True
rig.animation_data.action = action
scene.render.fps = fps
scene.frame_start, scene.frame_end = 0, frames
for frame, sample in enumerate(samples):
    scene.frame_set(frame)
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.location, bone.rotation_quaternion, bone.scale = sample[bone.name]
    # Rebuild the existing planted fan compensation at every exported sample;
    # fractional retiming must not interpolate the supporting feet off ground.
    bpy.context.view_layer.update()
    for index in range(8):
        fan = rig.pose.bones[f'rootfan_{index:02d}']
        fan.matrix = fan.bone.matrix_local.copy()
    for bone in rig.pose.bones:
        bone.keyframe_insert('location', frame=frame, group=bone.name)
        bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
        bone.keyframe_insert('scale', frame=frame, group=bone.name)

def channels():
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    yield from bag.fcurves

for channel in channels():
    for key in channel.keyframe_points:
        key.interpolation = 'LINEAR'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
export = OUT / 'Exports' / (PLAN['action'] + '.fbx')
bpy.ops.export_scene.fbx(filepath=str(export), object_types={'ARMATURE'}, use_selection=True,
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
    add_leaf_bones=False, use_armature_deform_only=True, armature_nodetype='NULL', path_mode='STRIP',
    use_mesh_modifiers=False, bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.)
for channel in channels():
    for key in channel.keyframe_points:
        key.co.x *= 30. / fps
        key.handle_left.x *= 30. / fps
        key.handle_right.x *= 30. / fps
scene.render.fps = 30
scene.frame_end = 96
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.location = (0, 0, 0)
    bone.rotation_quaternion = (1, 0, 0, 0)
    bone.scale = (1, 1, 1)
scene.frame_set(0)
blend = OUT / 'Authoring/M14_ImpactSlam_v22.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
report = dict(PLAN, source_blend=str(source), blend=str(blend), fbx=str(export),
              original_duration_seconds=3.2, original_contact_seconds=1.2,
              contact_frame_60hz=round(PLAN['contact_seconds'] * fps),
              contact_pose_and_hardware_preserved=True, geometry_and_skin_preserved=True,
              runtime_tested=False, rendered=False)
(OUT / 'Records/authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M14_V22_SLAM_AUTHORED ' + str(export), flush=True)
