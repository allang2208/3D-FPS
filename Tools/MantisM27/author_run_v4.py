"""Bake a low, forward hunting run from native Mutant3/Khaimera motion.

Preserves M27 BindingV2 mesh/weights; only exports a new animation clip.
"""
from pathlib import Path
import json, math
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT = BASE / 'RunV4'
OUT = ROOT / 'Delivery'
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((ROOT / 'native_run_poses.json').read_text(encoding='utf-8'))
ROLE = 'FeralRun'
FPS = 60
source = DATA['clips'][ROLE]
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'BindingV2/Delivery/MantisM27_BindingV2.blend'))
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = FPS, 1
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
names = [b.name for b in rig.data.bones]
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}
rig.animation_data.action = bpy.data.actions['A_M27_Idle_BindingV2']
if rig.animation_data.action.slots:
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(1)
idle = {n: rig.pose.bones[n].matrix.copy() for n in names}
rig.animation_data.action = None
for track in rig.animation_data.nla_tracks:
    track.mute = True
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
reflection = Matrix.Diagonal((1., -1., 1.))
helpers = lambda n: n.startswith(('blade_', 'hand_', 'ball_', 'headfront', 'head_tip', 'chain_', 'membrane_'))
forward = rest['headfront'].translation - rest['head'].translation
forward.z = 0
forward.normalize()
up = Vector((0, 0, 1))
pitch_axis = up.cross(forward).normalized()

def descendants(n, ancestor):
    while n:
        if n == ancestor:
            return True
        n = parent[n]
    return False

def build(rot, hip):
    result = {}
    for n in names:
        m = result[parent[n]] @ local[n] if parent[n] else local[n].copy()
        if n in rot:
            p = m.translation.copy()
            m = rot[n].to_matrix().to_4x4()
            m.translation = p
        if n == 'pelvis':
            m.translation = hip
        result[n] = m
    return result

raw = []
ref = source['reference']
for frame in source['frames']:
    rotations = {}
    for n in names:
        if helpers(n):
            continue
        delta = Quaternion(frame[n]['q']) @ Quaternion(ref[n]['q']).inverted()
        rotations[n] = (reflection @ delta.to_matrix() @ reflection).to_quaternion() @ rest[n].to_quaternion()
    hip = rest['pelvis'].translation + reflection @ (Vector(frame['pelvis']['p']) - Vector(ref['pelvis']['p']))
    raw.append(build(rotations, hip))

# Sole offsets are measured from the existing rigid foot-core weights. They
# drive the offline contact fit; the model and its weights are never changed.
weights = np.load(BASE / 'BindingV2/binding_weights_v2.npz')
topology = np.load(BASE / 'BindingV2/connected_source.npz')
points = topology['points']
ground = points[:, 1].min()
points = np.column_stack((points[:, 0], -points[:, 2], points[:, 1] - ground)) * 100
wi = {n: i for i, n in enumerate(weights['names'])}
soles, foot_targets, foot_rotations = {}, {}, {}
speeds = []
for side in ['l', 'r']:
    n = 'foot_' + side
    ids = weights['weights'][:, wi[n]] > .999
    soles[side] = np.asarray([rest[n].inverted() @ Vector(p) for p in points[ids]])
    foot_rotations[side] = [idle[n].to_quaternion().slerp(m[n].to_quaternion(), .7) for m in raw]
    lows = [float((soles[side] @ np.asarray(q.to_matrix()).T)[:, 2].min())
            for q in foot_rotations[side]]
    bottom = np.asarray([m[n].translation.z + low for m, low in zip(raw, lows)])
    height = bottom - bottom.min()
    foot_targets[side] = []
    for i, m in enumerate(raw):
        p = m[n].translation.copy()
        # Smoothly flatten the lowest 3 cm of the source sole arc. Swing height
        # and fore/aft trajectory remain driven by the complete donor stride.
        h = float(height[i])
        t = min(1., max(0., h / 3.))
        h *= t * t * (3 - 2 * t)
        p.z = h - lows[i]
        foot_targets[side].append(p)
        if i and max(height[i], height[i - 1]) < 5.:
            speed = -(m[n].translation - raw[i - 1][n].translation).dot(forward) * FPS
            if speed > 50:
                speeds.append(speed)

def fit_pose(m, index):
    rotations = {n: v.to_quaternion() for n, v in m.items() if not helpers(n)}
    # Put the bend in the waist/spine, not the character capsule or root.
    spine = m['spine_05'].translation - m['pelvis'].translation
    current = math.atan2(spine.dot(forward), spine.z)
    extra = max(math.radians(-8), min(math.radians(28), math.radians(40) - current))
    lean = Quaternion(pitch_axis, extra)
    for n in rotations:
        if descendants(n, 'spine_01'):
            rotations[n] = lean @ rotations[n]
    # Neck counter-rotation retains a forward hunting gaze.
    counter = Quaternion(pitch_axis, -extra * .38)
    for n in rotations:
        if descendants(n, 'neck_01'):
            rotations[n] = counter @ rotations[n]
    hip = m['pelvis'].translation - up * 8.
    lowered = build(rotations, hip)
    for side in ['l', 'r']:
        a, b, c = [part + '_' + side for part in ['thigh', 'calf', 'foot']]
        target = foot_targets[side][index]
        start = lowered[a].translation
        delta = target - start
        axis = delta.normalized()
        l1 = (rest[b].translation - rest[a].translation).length
        l2 = (rest[c].translation - rest[b].translation).length
        distance = max(abs(l1 - l2) + .01, min(delta.length, l1 + l2 - .01))
        pole = m[b].translation - m[a].translation
        pole -= axis * pole.dot(axis)
        if pole.length < .01:
            pole = forward - axis * forward.dot(axis)
        pole.normalize()
        along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
        knee = start + axis * along + pole * math.sqrt(max(0., l1 * l1 - along * along))
        endpoint = start + axis * distance
        rotations[a] = (m[b].translation - m[a].translation).rotation_difference(knee - start) @ m[a].to_quaternion()
        rotations[b] = (m[c].translation - m[b].translation).rotation_difference(endpoint - knee) @ m[b].to_quaternion()
        rotations[c] = foot_rotations[side][index]
    fitted = build(rotations, hip)
    for side in ['l', 'r']:
        upper, lower, hand = ['%s_%s' % (part, side) for part in ['upperarm', 'lowerarm', 'hand']]
        # Fold each entire forearm slightly further with the donor elbow plane.
        elbow_axis = (fitted[lower].translation - fitted[upper].translation).cross(
            fitted[hand].translation - fitted[lower].translation)
        if elbow_axis.length > .01:
            rotations[lower] = Quaternion(elbow_axis.normalized(), math.radians(12)) @ rotations[lower]
            fitted = build(rotations, hip)
        shoulder = fitted[upper].translation
        blade = [fitted['blade_' + part + '_' + side].translation for part in ['root', 'mid', 'tip']]
        lowest = min(blade, key=lambda p: p.z)
        direction = lowest - shoulder
        if lowest.z < 20. and direction.length > .01:
            axis = direction.cross(up)
            angle = math.asin(max(-1., min(1., (20. - shoulder.z) / direction.length))) - math.asin(direction.z / direction.length)
            if axis.length > .01:
                turn = Quaternion(axis.normalized(), max(0., angle))
                for part in [upper, lower]:
                    rotations[part] = turn @ rotations[part]
                fitted = build(rotations, hip)
    return fitted

poses = [fit_pose(m, i) for i, m in enumerate(raw)]
poses[-1] = {n: m.copy() for n, m in poses[0].items()}
natural_speed = float(np.median(speeds)) if speeds else 300.
# Set the authored playback rate and travel speed together. No root translation
# is added: the existing CharacterMovement and navigation still own travel.
run_speed = 340.
action = bpy.data.actions.new('A_M27_HunchedRun_RunV4')
action.use_fake_user = True
rig.animation_data.action = action
scene.frame_start, scene.frame_end = 1, len(poses)
for i, m in enumerate(poses):
    for n in names:
        basis = local[n].inverted() @ (m[parent[n]].inverted() @ m[n] if parent[n] else m[n])
        pb = rig.pose.bones[n]
        pb.location = basis.translation
        pb.rotation_mode = 'QUATERNION'
        q = basis.to_quaternion()
        if i and pb.rotation_quaternion.dot(q) < 0:
            q.negate()
        pb.rotation_quaternion, pb.scale = q, (1, 1, 1)
        pb.keyframe_insert('location', frame=i + 1, group=n)
        pb.keyframe_insert('rotation_quaternion', frame=i + 1, group=n)
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
filename = action.name + '.fbx'
bpy.ops.export_scene.fbx(filepath=str(OUT / filename), use_selection=True, object_types={'ARMATURE'},
    apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1, axis_forward='-Y', axis_up='Z',
    add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=True,
    bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MantisM27_RunV4.blend'))
manifest = {'revision': 'RunV4', 'file': filename, 'source': source['source'], 'fps': FPS,
            'seconds': source['seconds'], 'frames': len(poses), 'source_speed_cm_s': natural_speed,
            'run_speed_cm_s': run_speed, 'cloak_speed_cm_s': run_speed, 'mesh_revision': 'BindingV2',
            'source_license': 'Existing Epic Paragon Khaimera UE-only derivatives; not CC0; do not publicly redistribute.',
            'design': '40-degree torso target, 8 cm pelvis lowering, forward gaze, donor stride, fitted soles and scythes',
            'tested': False, 'rendered': False, 'runtime_tested': False}
(OUT / 'motion_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_RUN_V4_AUTHORED ' + json.dumps(manifest), flush=True)
