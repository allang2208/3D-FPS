"""Orient the actual rigid blade plane and cutting edge through an overhead arc."""
from pathlib import Path
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
SOURCE = BASE / 'PounceV6/Delivery'
ROOT = BASE / 'PounceV11'
OUT = ROOT / 'Delivery'
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'MantisM27_PounceV6.blend'))
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
blade_frames = {}
for side in ['l', 'r']:
    bone = 'blade_root_' + side
    inv = np.asarray(rest[bone].inverted())
    cloud = points[weights['weights'][:, wi[bone]] > .999]
    # The middle helper's position does not constrain blade roll. Fit the real
    # blade plane, then retain the signed curve bulge to distinguish edge/back.
    plane_normal = Vector(np.linalg.svd(cloud - cloud.mean(axis=0), full_matrices=False)[2][-1])
    chord = rest['blade_tip_' + side].translation - rest[bone].translation
    chord = (chord - plane_normal * chord.dot(plane_normal)).normalized()
    bulge = rest['blade_mid_' + side].translation - rest[bone].translation
    bend = plane_normal.cross(chord).normalized()
    if bend.dot(bulge) < 0.:
        bend.negate()
    blade_frames[side] = (chord, bend)
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
    if role == 'PounceWindup':
        active = smooth((time - .18) / .40)
    elif role == 'PounceFlight':
        active = 1.
    else:
        active = 1. - smooth((time - .16) / .56)
    return active, 18. + 5. * active

def elevation(role, time):
    # Same coherent late-flight downstroke as the existing Mutant3 reference:
    # its native 0.60--0.88 s cut maps to flight 0.402--0.619 s.
    # A single vertical arc replaces V9's crossing and independent elbow solve.
    if role == 'PounceWindup':
        return math.radians(80.)
    if role == 'PounceFlight':
        return math.radians(80. + 10. * smooth(time / .20) -
                            112. * smooth((time - .34) / .31))
    return math.radians(-22. - 4. * smooth(time / .10) + 6. * smooth((time - .13) / .23))

def overhead_turn(frame, side):
    m = frame['matrices']
    shoulder = m['upperarm_' + side].translation
    lateral = m['upperarm_l'].translation - m['upperarm_r'].translation
    lateral.z = 0.
    lateral.normalize()
    forward = lateral.cross(Vector((0., 0., 1.))).normalized()
    angle = elevation(frame['role'], frame['time'])
    up = Vector((0., 0., 1.))
    # At the top the concave cutting side faces forward. As the blade sweeps
    # forward, that same edge rotates down with the arc instead of lying flat.
    goal_chord = forward * math.cos(angle) + up * math.sin(angle)
    goal_bend = -forward * math.sin(angle) + up * math.cos(angle)
    def axes(a, b):
        a = a.normalized()
        b = (b - a * b.dot(a)).normalized()
        return Matrix((a, b, a.cross(b))).transposed().to_quaternion()
    current = m['blade_root_' + side].to_quaternion() @ rest['blade_root_' + side].to_quaternion().inverted()
    chord, bend = blade_frames[side]
    turn = axes(goal_chord, goal_bend) @ axes(current @ chord, current @ bend).inverted()
    active, _ = parameters(frame['role'], frame['time'], frame['duration'])
    return Quaternion().slerp(turn, active)

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
    ground_shoulder_z = shoulder.z
    if role == 'PounceFlight':
        # Anticipate the grounded pelvis so the last airborne cut has the same
        # blade-clearance requirement as the first grounded pose.
        ground_shoulder_z += frame.get('landing_offset_z', 0.) * smooth((time - .40) / .25)
    planes.append((Vector((0., 0., 1.)), 8. * active - ground_shoulder_z))
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
    action = bpy.data.actions['A_M27_' + role + '_PounceV6']
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for i in range(info['frames']):
        scene.frame_set(i + 1)
        matrices = {n: rig.pose.bones[n].matrix.copy() for n in names}
        frame = {'role': role, 'index': i, 'time': min(i / FPS, info['seconds']),
                 'duration': info['seconds'], 'matrices': matrices,
                 'basis': {n: rig.pose.bones[n].matrix_basis.copy() for n in names}, 'turn': {}}
        frames.append(frame)

land_start = next(f for f in frames if f['role'] == 'PounceLand')
for frame in frames:
    if frame['role'] == 'PounceFlight':
        frame['landing_offset_z'] = land_start['matrices']['pelvis'].translation.z - frame['matrices']['pelvis'].translation.z
    for side in ['l', 'r']:
        frame['turn'][side] = project_arm(frame, side, overhead_turn(frame, side))

# Smooth the correction across all three phases, including their boundaries.
# Re-project the smooth result into the blade separation/ground constraints.
for side in ['l', 'r']:
    turns = [frame['turn'][side].copy() for frame in frames]
    for i, frame in enumerate(frames):
        # Average in one quaternion hemisphere. Axis-angle averaging can turn
        # equivalent q/-q into a large false rotation near the 180-degree seam.
        value = [0., 0., 0., 0.]
        centre = turns[i]
        for step, weight in [(-2, 1), (-1, 4), (0, 6), (1, 4), (2, 1)]:
            q = turns[min(len(turns)-1, max(0, i + step))].copy()
            if q.dot(centre) < 0.:
                q.negate()
            for axis in range(4):
                value[axis] += q[axis] * weight
        frame['turn'][side] = project_arm(frame, side, Quaternion(value).normalized())

result = {'revision': 'PounceV11', 'source_revision': 'PounceV6', 'rejected_revisions': ['PounceV9', 'PounceV10'], 'mesh_revision': 'BindingV2',
          'fps': FPS, 'clips': {}, 'source_license': manifest['source_license'],
          'edited_rotation_tracks': ['upperarm_l', 'upperarm_r'],
          'design': 'Geometry-derived blade planes and signed cutting edges; overhead to forward/down arc; V6 coherent arm chain',
          'reference': 'Mutant3 pounce_arm_refine coherent native Khaimera downstroke, already retargeted in V5/V6',
          'flight_downstroke_seconds': [.34, .65], 'blade_half_gap_cm': [18., 23.], 'ground_clearance_cm': 8.,
          'native_code_changed': False, 'runtime_tested': False, 'rendered': False}
for role in roles:
    action = bpy.data.actions.new('A_M27_' + role + '_PounceV11')
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
    print('M27_POUNCE_V11_EXPORTED ' + role, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MantisM27_PounceV11.blend'))
(OUT / 'motion_manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('M27_POUNCE_V11_AUTHORED', flush=True)
