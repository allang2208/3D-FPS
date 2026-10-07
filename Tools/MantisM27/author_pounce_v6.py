"""Separate M27's rigid scythes by rotating complete arm chains, offline only."""
from pathlib import Path
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
SOURCE = BASE / 'PounceV5/Delivery'
ROOT = BASE / 'PounceV6'
OUT = ROOT / 'Delivery'
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'MantisM27_PounceV5.blend'))
scene = bpy.context.scene
scene.render.fps = FPS = 60
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for track in rig.animation_data.nla_tracks:
    track.mute = True
names = [b.name for b in rig.data.bones]
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}

# Use a conservative cage of the actual rigid blade surface, not merely its
# three helper points. Each slice box encloses all source vertices in that slice.
weights = np.load(BASE / 'BindingV2/binding_weights_v2.npz')
topology = np.load(BASE / 'BindingV2/connected_source.npz')
points = topology['points']
ground = points[:, 1].min()
points = np.column_stack((points[:, 0], -points[:, 2], points[:, 1] - ground)) * 100
wi = {n: i for i, n in enumerate(weights['names'])}
cages = {}
for side in ['l', 'r']:
    bone = 'blade_root_' + side
    inv = np.asarray(rest[bone].inverted())
    cloud = points[weights['weights'][:, wi[bone]] > .999]
    cloud = cloud @ inv[:3, :3].T + inv[:3, 3]
    principal = np.linalg.svd(cloud - cloud.mean(axis=0), full_matrices=False)[2][0]
    distance = cloud @ principal
    bins = np.minimum(13, ((distance - distance.min()) / max(.01, np.ptp(distance)) * 14).astype(int))
    cage = []
    for k in range(14):
        section = cloud[bins == k]
        if not len(section):
            continue
        lo, hi = section.min(axis=0), section.max(axis=0)
        cage.extend(Vector((x, y, z)) for x in [lo[0], hi[0]] for y in [lo[1], hi[1]] for z in [lo[2], hi[2]])
    cages[side] = cage

def smooth(t):
    t = min(1., max(0., t))
    return t * t * (3. - 2. * t)

def parameters(role, time, duration):
    # Shared values at phase boundaries; spread opens before takeoff and releases
    # with the existing return to idle, rather than snapping on at flight start.
    if role == 'PounceWindup':
        active = smooth(time / .32)
        half_gap = 18. + 6. * active
    elif role == 'PounceFlight':
        active = 1.
        half_gap = 24. + 4. * math.sin(math.pi * time / duration) ** 2
    else:
        active = 1. - smooth((time - .12) / max(.01, duration - .28))
        half_gap = 18. + 6. * active
    return active, half_gap

def project_arm(frame, side, turn):
    matrices, role, time, duration = frame['matrices'], frame['role'], frame['time'], frame['duration']
    shoulder = matrices['upperarm_' + side].translation
    left = matrices['upperarm_l'].translation
    right = matrices['upperarm_r'].translation
    centre = (left + right) * .5
    lateral = left - right
    lateral.z = 0.
    lateral.normalize()
    outward = lateral if side == 'l' else -lateral
    active, half_gap = parameters(role, time, duration)
    points = [matrices['blade_root_' + side] @ p - shoulder for p in cages[side]]
    planes = [(outward, half_gap - (shoulder - centre).dot(outward))]
    if role != 'PounceFlight':
        planes.append((Vector((0., 0., 1.)), 8. * active - shoulder.z))
    # Alternating projections apply a minimal whole-arm rotation about the
    # shoulder. Forearm, hand and rigid blade keep their authored relative pose.
    for _ in range(48):
        settled = True
        for normal, minimum in planes:
            rotated = [turn @ p for p in points]
            low = min(rotated, key=lambda p: p.dot(normal))
            if low.dot(normal) >= minimum - .01:
                continue
            settled = False
            length = low.length
            current = math.acos(max(-1., min(1., low.dot(normal) / length)))
            desired = math.acos(max(-1., min(1., (minimum + .08) / length)))
            axis = low.cross(normal)
            if axis.length < 1.e-5:
                axis = normal.cross(Vector((0., 0., 1.)))
                if axis.length < 1.e-5:
                    axis = Vector((1., 0., 0.))
            turn = Quaternion(axis.normalized(), max(0., current - desired)) @ turn
        if settled:
            break
    return turn.normalized()

frames = []
roles = ['PounceWindup', 'PounceFlight', 'PounceLand']
for role in roles:
    info = manifest['clips'][role]
    action = bpy.data.actions['A_M27_' + role + '_PounceV5']
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for i in range(info['frames']):
        scene.frame_set(i + 1)
        matrices = {n: rig.pose.bones[n].matrix.copy() for n in names}
        frame = {'role': role, 'index': i, 'time': min(i / FPS, info['seconds']),
                 'duration': info['seconds'], 'matrices': matrices,
                 'basis': {n: rig.pose.bones[n].matrix_basis.copy() for n in names}, 'turn': {}}
        active, _ = parameters(role, frame['time'], frame['duration'])
        for side in ['l', 'r']:
            shoulder = matrices['upperarm_' + side].translation
            mid = matrices['blade_mid_' + side].translation - shoulder
            # Left blade leads slightly higher; right blade trails lower. The
            # paired attack still hits at its original shared landing moment.
            offset = Vector((0., -4. if side == 'l' else 4., 10. if side == 'l' else -4.)) * active
            seed = mid.rotation_difference(mid + offset)
            frame['turn'][side] = project_arm(frame, side, seed)
        frames.append(frame)

# Smooth the correction across all three phases, including their boundaries.
# Re-project the smooth result into the blade separation/ground constraints.
for side in ['l', 'r']:
    logs = [frame['turn'][side].to_exponential_map() for frame in frames]
    for i, frame in enumerate(frames):
        value = Vector((0., 0., 0.))
        for step, weight in [(-2, 1), (-1, 4), (0, 6), (1, 4), (2, 1)]:
            value += logs[min(len(logs)-1, max(0, i + step))] * (weight / 16.)
        frame['turn'][side] = project_arm(frame, side, Quaternion(value))

result = {'revision': 'PounceV6', 'source_revision': 'PounceV5', 'mesh_revision': 'BindingV2',
          'fps': FPS, 'clips': {}, 'source_license': manifest['source_license'],
          'edited_rotation_tracks': ['upperarm_l', 'upperarm_r'],
          'design': 'Open windup; separated asymmetrical scythes in flight; bilateral landing cuts; whole-arm rotations',
          'blade_half_gap_cm': [18., 28.], 'ground_clearance_cm': 8.,
          'native_code_changed': False, 'runtime_tested': False, 'rendered': False}
for role in roles:
    action = bpy.data.actions.new('A_M27_' + role + '_PounceV6')
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.frame_start, scene.frame_end = 1, manifest['clips'][role]['frames']
    for frame in (f for f in frames if f['role'] == role):
        bases = {n: m.copy() for n, m in frame['basis'].items()}
        for side in ['l', 'r']:
            n = 'upperarm_' + side
            pose = frame['matrices'][n].copy()
            rotation = frame['turn'][side] @ pose.to_quaternion()
            rotated = rotation.to_matrix().to_4x4()
            rotated.translation = pose.translation
            relative = local[n].inverted() @ frame['matrices'][parent[n]].inverted() @ rotated
            # Only change the local shoulder rotation. No joint translation,
            # scale, elbow twist, reference pose or skin weights are authored.
            bases[n] = Matrix.LocRotScale(bases[n].translation, relative.to_quaternion(), bases[n].to_scale())
        for n in names:
            pb = rig.pose.bones[n]
            pb.location, pb.rotation_mode, pb.scale = bases[n].translation, 'QUATERNION', bases[n].to_scale()
            q = bases[n].to_quaternion()
            if frame['index'] and pb.rotation_quaternion.dot(q) < 0.:
                q.negate()
            pb.rotation_quaternion = q
            for channel in ['location', 'rotation_quaternion', 'scale']:
                pb.keyframe_insert(channel, frame=frame['index'] + 1, group=n)
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
    result['clips'][role] = {**manifest['clips'][role], 'file': filename}
    print('M27_POUNCE_V6_EXPORTED ' + role, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MantisM27_PounceV6.blend'))
(OUT / 'motion_manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_POUNCE_V6_AUTHORED', flush=True)
