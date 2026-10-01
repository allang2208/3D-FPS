"""Repair only the accepted Rampage slam's recovery, retaining the V8 skin.

Source End supplies shoulder swing and the elbow plane. Rigid segment frames
return together to the existing ready pose; their axial offsets and volume
helpers share that return instead of switching donor reference at 1.55 s.
"""
import ast
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
V8 = ROOT / 'RampageV8'
SOURCE = ROOT / 'RampageReferenceIntake'
DELIVERY = OUT / 'Delivery/Animations'
DELIVERY.mkdir(parents=True, exist_ok=True)
ROLE = 'AttackSlam_R'
JOIN_FRAME = 32
JOIN_TIME = (JOIN_FRAME - 1) / 30.0
END_FRAME = 55
DURATION = 1.8

bpy.ops.wm.open_mainfile(filepath=str(V8 / 'HundredEyedSlag_RampageV8.blend'))
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in scene.objects if o.type == 'MESH')
arm = rig.data
rest = {b.name: b.matrix_local.copy() for b in arm.bones}
inv = {n: m.inverted() for n, m in rest.items()}
spec = json.loads((ROOT / 'AuthoringV1/skeleton_spec.json').read_text())
byname = {r['name']: r for r in spec}
meta = json.loads((ROOT / 'AuthoringV1/source_geometry.json').read_text())
limbs = {}
for key, pad in meta['feet_centres_m'].items():
    kind, side = key.split('.')
    names = [f'{kind}_{part}.{side}' for part in ('upper', 'lower', 'palm')]
    limb = {k: Vector(byname[n]['head']) for k, n in zip(('shoulder', 'elbow', 'wrist'), names)}
    limb.update(pad=Vector(pad), bones=names, parent=byname[names[0]]['parent'])
    limb['a'] = (limb['elbow'] - limb['shoulder']).length
    limb['b'] = (limb['wrist'] - limb['elbow']).length
    limb['axis'] = (limb['wrist'] - limb['shoulder']).normalized()
    pole = limb['elbow'] - limb['shoulder']
    limb['pole'] = (pole - limb['axis'] * pole.dot(limb['axis'])).normalized()
    limb['min_reach'] = math.sqrt(limb['a']**2 + limb['b']**2 + 2*limb['a']*limb['b']*math.cos(math.radians(112)))
    limb['max_reach'] = math.sqrt(limb['a']**2 + limb['b']**2 + 2*limb['a']*limb['b']*math.cos(math.radians(6)))
    limb['toes'] = [r['name'] for r in spec if r['name'].startswith(kind+'_digit_') and r['name'].endswith('.'+side)]
    limbs[key] = limb
d = limbs['front.R']

# Reuse production kinematics without running the old mesh/skin authoring.
namespace = globals()
keys = list(limbs)
for file, wanted in [
    (ROOT / 'RuntimeV3/author_runtime.py', {'smooth', 'step', 'rotation', 'around', 'aim', 'solve'}),
    (ROOT / 'HeroHandV4/author_hero_hand.py', {'core'}),
    (V8 / 'author_rampage.py', {'coordinates', 'mix', 'sample', 'warp', 'frame_basis', 'source_arm', 'axial', 'volume_helpers', 'pose'}),
]:
    for node in ast.parse(file.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), 'exec'), namespace)

u0 = (d['elbow'] - d['shoulder']).normalized()
l0 = (d['wrist'] - d['elbow']).normalized()
n0 = u0.cross(l0).normalized()
target_upper0, target_lower0 = frame_basis(u0, n0), frame_basis(l0, n0)
rest_bend = u0.angle(l0)

# The same actual palm extents as V8; this reads its inputs but changes no skin.
v = np.empty(len(mesh.data.vertices) * 3, np.float32)
mesh.data.vertices.foreach_get('co', v)
v = v.reshape(-1, 3)
target_points = [np.asarray(d[n]) for n in ('shoulder', 'elbow', 'wrist', 'pad')]
arc, distance = coordinates(v, target_points)
other_distance = np.minimum.reduce([
    coordinates(v, [np.asarray(l[n]) for n in ('shoulder', 'elbow', 'wrist', 'pad')])[1]
    for k, l in limbs.items() if k != 'front.R'
])
old_skin = np.load(ROOT / 'ApeRecoveryV7/skin_weights.npz')
skin_names = [str(n) for n in old_skin['bone_names']]
helper_names = ['front_shoulder.R', 'front_upper_twist.R', 'front_lower_twist_01.R',
                'front_lower_twist_02.R', 'front_elbow_support.R', 'front_wrist_support.R']
right_indices = [skin_names.index(n) for n in d['bones'] + helper_names + d['toes']]
old_right = (old_skin['weights'] * np.isin(old_skin['indices'], right_indices)).sum(1)
region = ((distance < .205) & (distance < other_distance + .01) & (arc > .04)
          & (v[:, 1] < -.25) & (v[:, 0] > -.1) & (v[:, 2] < .78))
region |= (old_right > .08) & (v[:, 0] > -.12) & (v[:, 2] < .78)
palm_vertices = v[region & (arc > d['a'] + d['b'] - .005)] - np.asarray(d['wrist'])

C = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, 1)))
sources = {}
for name in ['Idle', 'Ability_GroundSmash_Start', 'Ability_GroundSmash_End']:
    raw = json.loads((SOURCE / 'source_motion' / (name + '.json')).read_text())
    frames = []
    for row in raw['frames']:
        frame = {}
        for bone, t in row['component'].items():
            xyzw = t['rotation_xyzw']
            q = Quaternion((xyzw[3], xyzw[0], xyzw[1], xyzw[2]))
            frame[bone] = (C @ Vector(t['translation_cm']) * .01,
                           (C @ q.to_matrix() @ C.transposed()).to_quaternion())
        frames.append(frame)
    sources[name] = dict(frames=frames, seconds=raw['seconds'])

def ease(x):
    x = max(0.0, min(1.0, x))
    return x*x*x*(x*(x*6.0 - 15.0) + 10.0)

def shortest(a, b, f):
    b = b.copy()
    if a.dot(b) < 0:
        b.negate()
    return a.slerp(b, f)

def donor_time(t):
    if t <= 1.04:
        return max(0.0, (t - .82) / .22 * .25)
    return min(sources['Ability_GroundSmash_End']['seconds'], .25 + (t - 1.04) / .51 * .45)

def source_pose(role, t):
    # Only used for the recovery body's three supporting limbs after 1.55 s.
    # Blend actual End to Idle instead of abruptly changing the donor pose.
    neutral = sources['Idle']['frames'][0]
    src = sample('Ability_GroundSmash_End', donor_time(t))
    if t >= 1.55:
        src = mix(src, neutral, ease((t - 1.55) / (DURATION - 1.55)))
    return src, neutral

original = bpy.data.actions['A_HundredEyedSlag_AttackSlam_R_RampageV8']
rig.animation_data.action = original
rig.animation_data.action_slot = original.slots[0]
cached = {}
for frame in range(JOIN_FRAME, END_FRAME + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    cached[frame] = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
start, finish = cached[JOIN_FRAME], cached[END_FRAME]

def arm_frame(matrices):
    up = (matrices['front_lower.R'].translation - matrices['front_upper.R'].translation).normalized()
    lo = (matrices['front_palm.R'].translation - matrices['front_lower.R'].translation).normalized()
    normal = up.cross(lo).normalized()
    return frame_basis(up, normal), frame_basis(lo, normal), up.angle(lo)

start_upper, start_lower, start_bend = arm_frame(start)
end_upper, end_lower, end_bend = arm_frame(finish)
neutral = sources['Idle']['frames'][0]
src_start = sample('Ability_GroundSmash_End', donor_time(JOIN_TIME))
us, ls, ns, donor_start_bend, _, _, _ = source_arm(src_start, neutral)
donor_start_frame = frame_basis(us, ns)

offsets = {}
for bone, first_frame, last_frame in [
    ('front_upper.R', start_upper, end_upper),
    ('front_lower.R', start_lower, end_lower),
    ('front_palm.R', start_lower, end_lower),
    ('front_upper_twist.R', start_upper, end_upper),
    ('front_lower_twist_01.R', start_lower, end_lower),
    ('front_lower_twist_02.R', start_lower, end_lower),
]:
    offsets[bone] = (first_frame.inverted() @ start[bone].to_quaternion(),
                     last_frame.inverted() @ finish[bone].to_quaternion())

start_parent = start[d['parent']] @ inv[d['parent']]
start_shoulder_offset = start['front_upper.R'].translation - start_parent @ d['shoulder']

def repaired_pose(frame):
    t = (frame - 1) / 30.0
    if frame == END_FRAME:
        return {n: m.copy() for n, m in finish.items()}
    # Preserve the already-authored torso/support poses until the old late
    # donor switch. Only replace that discontinuous body's final handoff.
    target = (pose(ROLE, t, DURATION) if t >= 1.55
              else {n: m.copy() for n, m in cached[frame].items()})
    amount = ease((t - JOIN_TIME) / (DURATION - JOIN_TIME))
    donor = sample('Ability_GroundSmash_End', donor_time(t))
    us, ls, ns, bend, _, _, _ = source_arm(donor, neutral)
    donor_frame = frame_basis(us, ns)
    # Carry the real donor's recovery swing from the accepted contact frame;
    # return the complete geometric frame on one shortest quaternion arc.
    carried = donor_frame @ donor_start_frame.inverted() @ start_upper
    upper_frame = shortest(carried, end_upper, amount)
    upper_dir = upper_frame @ Vector((1, 0, 0))
    normal = upper_frame @ Vector((0, 0, 1))
    bend = bend + (start_bend - donor_start_bend) * (1 - amount)
    bend = bend * (1 - amount) + end_bend * amount
    bend = max(math.radians(6), min(math.radians(112), bend))
    lower_dir = Quaternion(normal, bend) @ upper_dir
    lower_frame = frame_basis(lower_dir, normal)

    parent = target[d['parent']] @ inv[d['parent']]
    # The same donor clavicle translation, smoothly withdrawn to the ready
    # attachment. The captured initial offset prevents a boundary jump.
    donor_clavicle_delta = ((donor['upperarm_r'][0] - donor['spine_03'][0])
                            - (src_start['upperarm_r'][0] - src_start['spine_03'][0])) * .74 * .55
    donor_clavicle_delta = Vector((max(-.075, min(.075, donor_clavicle_delta.x)),
                                  max(-.055, min(.055, donor_clavicle_delta.y)),
                                  max(-.04, min(.105, donor_clavicle_delta.z))))
    shoulder = parent @ d['shoulder'] + (start_shoulder_offset + donor_clavicle_delta) * (1 - amount)
    elbow = shoulder + upper_dir * d['a']
    wrist = elbow + lower_dir * d['b']
    palm_offset = shortest(*offsets['front_palm.R'], amount)
    palm_q = lower_frame @ palm_offset

    # Contact uses actual palm geometry, retaining the same hinge plane and
    # rigid lengths. Recompute the palm rotation after every reach adjustment.
    for _ in range(4):
        delta = palm_q @ rest['front_palm.R'].to_quaternion().inverted()
        floor_wrist = .012 - float((palm_vertices @ np.asarray(delta.to_matrix()).T)[:, 2].min())
        if wrist.z >= floor_wrist:
            break
        requested = wrist.copy()
        requested.z = floor_wrist
        axis = requested - shoulder
        reach = max(d['min_reach'], min(d['max_reach'], axis.length))
        axis.normalize()
        pole = elbow - shoulder - axis * (elbow - shoulder).dot(axis)
        if pole.length < 1e-5:
            pole = normal.cross(axis)
        pole.normalize()
        x = (d['a']**2 + reach**2 - d['b']**2) / (2 * reach)
        height = math.sqrt(max(0.0, d['a']**2 - x*x))
        elbow = shoulder + axis*x + pole*height
        wrist = shoulder + axis*reach
        upper_dir = (elbow - shoulder).normalized()
        lower_dir = (wrist - elbow).normalized()
        contact_normal = upper_dir.cross(lower_dir)
        if contact_normal.length > 1e-5:
            contact_normal.normalize()
            if contact_normal.dot(normal) < 0:
                contact_normal.negate()
            normal = contact_normal
        upper_frame, lower_frame = frame_basis(upper_dir, normal), frame_basis(lower_dir, normal)
        palm_q = lower_frame @ palm_offset

    for bone, location, geometric in [
        ('front_upper.R', shoulder, upper_frame),
        ('front_lower.R', elbow, lower_frame),
        ('front_palm.R', wrist, lower_frame),
    ]:
        q = geometric @ shortest(*offsets[bone], amount)
        target[bone] = Matrix.LocRotScale(location, q, Vector((1, 1, 1)))
    for bone, parent_name, geometric in [
        ('front_upper_twist.R', 'front_upper.R', upper_frame),
        ('front_lower_twist_01.R', 'front_lower.R', lower_frame),
        ('front_lower_twist_02.R', 'front_lower.R', lower_frame),
    ]:
        location = (target[parent_name] @ inv[parent_name] @ rest[bone]).translation
        q = geometric @ shortest(*offsets[bone], amount)
        target[bone] = Matrix.LocRotScale(location, q, Vector((1, 1, 1)))
    for helper, a, b, anchor in [
        ('front_elbow_support.R', 'front_upper.R', 'front_lower.R', 'front_lower.R'),
        ('front_wrist_support.R', 'front_lower.R', 'front_palm.R', 'front_palm.R'),
    ]:
        qa = (target[a] @ inv[a]).to_quaternion()
        qb = (target[b] @ inv[b]).to_quaternion()
        q = shortest(qa, qb, .5) @ rest[helper].to_quaternion()
        target[helper] = Matrix.LocRotScale(target[anchor].translation, q, Vector((1, 1, 1)))
    cap = shortest((target['chest'] @ inv['chest']).to_quaternion(),
                   (target['front_upper.R'] @ inv['front_upper.R']).to_quaternion(), .45)
    target['front_shoulder.R'] = Matrix.LocRotScale(shoulder, cap @ rest['front_shoulder.R'].to_quaternion(), Vector((1, 1, 1)))
    for toe in d['toes']:
        target[toe] = target['front_palm.R'] @ inv['front_palm.R'] @ rest[toe]
    target['attack_origin'] = target['front_palm.R'] @ inv['front_palm.R'] @ rest['attack_origin']
    return target

action = original.copy()
action.name = 'A_HundredEyedSlag_AttackSlam_R_RampageRecoverV9'
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
channelbag = action.layers[0].strips[0].channelbag(action.slots[0])
for curve in channelbag.fcurves:
    for point in reversed(list(curve.keyframe_points)):
        if point.co.x > JOIN_FRAME:
            curve.keyframe_points.remove(point, fast=True)
    curve.update()
scene.frame_set(JOIN_FRAME)
bpy.context.view_layer.update()
previous = {pb.name: pb.rotation_quaternion.copy() for pb in rig.pose.bones}
paths = []
for frame in range(JOIN_FRAME + 1, END_FRAME + 1):
    target = repaired_pose(frame)
    for bone in arm.bones:
        n = bone.name
        if n not in target:
            parent = bone.parent.name if bone.parent else None
            target[n] = target[parent] @ inv[parent] @ rest[n] if parent else rest[n].copy()
        basis = (inv[n] @ rest[bone.parent.name] @ target[bone.parent.name].inverted() @ target[n]
                 if bone.parent else inv[n] @ target[n])
        pb = rig.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = basis
        pb.rotation_quaternion.make_compatible(previous[n])
        previous[n] = pb.rotation_quaternion.copy()
        pb.scale = (1, 1, 1)
        for channel in ('location', 'rotation_quaternion', 'scale'):
            pb.keyframe_insert(channel, frame=frame)
    paths.append(dict(frame=frame, seconds=(frame-1)/30.0,
                      shoulder_m=list(target['front_upper.R'].translation),
                      elbow_m=list(target['front_lower.R'].translation),
                      wrist_m=list(target['front_palm.R'].translation)))
for curve in channelbag.fcurves:
    for point in curve.keyframe_points:
        if point.co.x > JOIN_FRAME:
            point.interpolation = 'LINEAR'

scene.frame_start = 1
scene.frame_end = END_FRAME
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'HundredEyedSlag_RampageRecoverV9.blend'))
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
fbx = DELIVERY / 'A_HundredEyedSlag_AttackSlam_R_RampageRecoverV9.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx), object_types={'ARMATURE'}, bake_anim=True,
    use_selection=True, add_leaf_bones=False, use_armature_deform_only=False,
    axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0)
receipt = dict(revision='RampageRecoverV9', base_revision='RampageV8', role=ROLE,
    action=action.name, fbx=str(fbx), seconds=DURATION, fps=30, end_frame_inclusive=END_FRAME,
    preserved_keys_frames_inclusive=[1, JOIN_FRAME], recovery_rewritten_frames_inclusive=[JOIN_FRAME+1, END_FRAME],
    preserved_strike_seconds_inclusive=[0, JOIN_TIME], native_hit_window_s=[.84, 1.00],
    sweep_reauthored=False, mesh_reweighted=False, mesh_reimport_required=False,
    recovery_source='Epic Rampage Ability_GroundSmash_End, continuous geometric-frame return to existing ready pose',
    adaptations=['Captured accepted contact pose', 'Coupled rigid shoulder/elbow/wrist return',
                 'Continuous elbow plane, shortest quaternion arcs', 'Synchronous axial offsets and twist helpers',
                 'Continuous End-to-Idle torso/support transition after 1.55 s', 'Actual palm-floor contact'],
    paths=paths, preview_rendered=False, runtime_tested=False)
(OUT / 'authoring_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RAMPAGE_RECOVER_V9_AUTHORED_AND_EXPORTED', flush=True)
