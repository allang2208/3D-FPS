"""Original M07 hind-limb anatomy, source-derived controls, weights and motion.

The accepted canine NaturalV3 production method is adapted to two supported
biped feet. Its smoothed source controls and independently constrained hock
are retained; canine gallop timing and local bone rotations are not copied.
Only original-source limb joints, skin weights and action curves are authored.
"""
from pathlib import Path
import argparse
import json
import math

import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'RecoveryOriginalV07/legs'
CANINE = Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924')
SOURCE = CANINE / 'GodotRunFitV2/Source/godot_gallop_samples.json'
CHAIN = ('thigh', 'calf', 'hock', 'foot', 'ball')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*x*(x*(x*6.-15.)+10.)


def controls():
    src = json.loads(SOURCE.read_text(encoding='utf-8'))
    # Exactly the accepted NaturalV3 control smoothing, before contact/IK.
    raw = src['samples'][:-1]
    count = len(raw)
    kernel = ((-2, .035), (-1, .18), (0, .57), (1, .18), (2, .035))
    fields = {}
    for name in ('BackLeg.L', 'BackUpperLeg.L', 'BackLowerLeg.L', 'IKBackLeg.L', 'FFB.L'):
        p = np.asarray([row[name]['head'] for row in raw], dtype=np.float64)
        fields[name] = sum(np.roll(p, -d, axis=0)*w for d, w in kernel)
    foot = fields['FFB.L']
    floor = float(foot[:, 2].min())
    # The source has a running contact interval. Retiming it to a walking
    # duty factor is deliberate; it does not retain four-foot gallop phase.
    contact = 1.-smooth((foot[:, 2]-floor-.002)/.020)
    active = contact > .15
    runs = []
    for start in range(count):
        if active[start] and not active[(start-1) % count]:
            length = 0
            while active[(start+length) % count] and length < count:
                length += 1
            runs.append((length, start))
    if not runs:
        start = int(np.argmin(foot[:, 2])); length = 2
    else:
        length, start = max(runs)
    # Curve sample at the stance boundaries. Native cyclic cubic interpolation
    # is used again by the final Blender authoring helper.
    shank = fields['IKBackLeg.L']-fields['BackLowerLeg.L']
    shank /= np.linalg.norm(shank, axis=1)[:, None]
    angles = np.unwrap(np.arctan2(shank[:, 1], -shank[:, 2]))
    return {'source': str(SOURCE), 'source_action': src['action'],
        'source_period_seconds': 17/30, 'source_frames_including_endpoint': len(src['samples']),
        'kernel': [list(k) for k in kernel],
        'stance_start_phase': start/count, 'stance_end_phase': (start+length)/count,
        'source_contact_floor_m': floor,
        'foot_head_m': foot.tolist(), 'hock_direction': shank.tolist(),
        'hock_sagittal_angle_mean': float(angles.mean()),
        'hock_sagittal_angle': angles.tolist(),
        'adaptation': 'Single smoothed hind leg is retimed to biped stance/swing; opposite leg is half a target cycle later. Source local bone rotations and gallop body travel are not transferred.'}


def anatomy(region_path=None):
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    p = source['positions'].astype(np.float64)
    faces = source['indices'].reshape(-1, 3)
    region_path = Path(region_path or ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    labels = np.load(region_path)['face_labels']
    body = p[np.unique(faces[labels == 0])]
    joints = {}; profiles = {}; tips = {}
    for side, sign in (('l', 1), ('r', -1)):
        leg = body[(body[:, 0]*sign > .018) & (body[:, 0]*sign < .245) & (body[:, 1] < -.11)]
        rows = []
        for y in np.arange(-.15, -.71, -.025):
            q = leg[np.abs(leg[:, 1]-y) < .010]
            if len(q):
                center = (np.quantile(q, .08, axis=0)+np.quantile(q, .92, axis=0))*.5
                rows.append({'source_y': float(y), 'source_center': center.tolist(), 'source_vertex_count': len(q)})
        profiles[side] = rows
        # Original thigh-to-backward-kink-to-foot silhouette is retained. The
        # upper articulation is placed inside the actual thigh; the pronounced
        # lower rear kink is given its own hock rather than one long human shin.
        for bone, y in (('thigh', -.150), ('calf', -.260), ('hock', -.462), ('foot', -.670)):
            q = leg[np.abs(leg[:, 1]-y) < .013]
            lo, hi = np.quantile(q, .08, axis=0), np.quantile(q, .92, axis=0)
            center = (lo+hi)*.5
            if bone == 'calf':
                # The source's broad thigh has no independently rigged knee.
                # Use the interior anterior quarter of its depth, so the new
                # knee and pronounced posterior hock have opposing planes even
                # in the neutral reference; do not reverse-bend at frame one.
                center[2] = lo[2]*.25+hi[2]*.75
            center[1] = y
            joints[bone+'_'+side] = center.tolist()
        q = leg[(leg[:, 1] < -.708) & (leg[:, 1] > -.737) & (leg[:, 2] > .015)]
        center = (np.quantile(q, .08, axis=0)+np.quantile(q, .92, axis=0))*.5
        center[1] = -.728
        # Forefoot breadth belongs to one supporting pad. It is not divided
        # into independently wandering toe pieces.
        joints['ball_'+side] = center.tolist()
        q = leg[(leg[:, 1] < -.720) & (leg[:, 2] > .09)]
        tip = np.median(q, axis=0)
        tip[1] = max(float(p[:, 1].min()), -.740)
        tip[2] = float(np.quantile(q[:, 2], .93))
        tips['ball_'+side] = tip.tolist()
    record = {'revision': 'OriginalV07', 'original_geometry_source': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'joints_source': joints, 'joint_guides_source': joints, 'bone_tips_source': tips,
        'source_coordinates': 'GLB X lateral, Y vertical, Z forward; no geometry replacement',
        'scale_to_meters': float(3.1/(p[:, 1].max()-p[:, 1].min())), 'ground_source_y': float(p[:, 1].min()),
        'bone_parents': {n+'_'+s: (CHAIN[i-1]+'_'+s if i else 'pelvis') for s in ('l', 'r') for i, n in enumerate(CHAIN)},
        'new_deform_bones': ['hock_l', 'hock_r'],
        'bend_planes': {s: {'plane_normal_blender': [1, 0, 0], 'knee_pole_blender': [0, -1, 0],
            'hock_pole_blender': [0, 1, 0], 'minimum_knee_flexion_degrees': 14,
            'hock_control_limit_degrees': 22} for s in ('l', 'r')},
        'source_leg_sections': profiles,
        'method': 'Original body cross-section extrema center hip, posterior hock, ankle and coherent forefoot; the upper knee is fitted to the interior anterior quarter of thigh depth to retain independent forward-knee/backward-hock planes. Dog hind-leg mechanics are fitted to this source silhouette; the visible body is not rebuilt.',
        'gait': {'SlowWalk': {'duration_seconds': 50/30, 'speed_cm_s': 90, 'stance_fraction': .68, 'pelvis_crouch_cm': 11},
                 'Chase': {'duration_seconds': 36/30, 'speed_cm_s': 145, 'stance_fraction': .60, 'pelvis_crouch_cm': 14},
                 'bilateral_phase_offset_cycles': .5, 'source_controls': str(OUT/'canine_hindleg_controls_v07.json')},
        'tested': False, 'rendered': False, 'user_visual_accepted': False,
        'limitations': ['Joint placement is a production anatomical fit to a generated source surface, not verified living anatomy.',
            'Biped gait is an authored adaptation of accepted canine hind-leg controls, not a copied quadruped action or measured M07 motion capture.']}
    write_json(OUT/'hindleg_anatomy_v07.json', record)
    write_json(OUT/'canine_hindleg_controls_v07.json', controls())
    return record


def apply_reference(rig, unit_scale=None):
    """Apply original-source hip/knee/hock/ankle/pad to a rig in Edit mode.

    Call before making any action. Unit scale is 1 for Blender metre source,
    100 for a centimetre-native source. All other bone joints are left intact.
    """
    import bpy
    from mathutils import Vector, Matrix
    record = json.loads((OUT/'hindleg_anatomy_v07.json').read_text(encoding='utf-8'))
    unit_scale = unit_scale or (100 if rig.data.bones['pelvis'].head_local.z > 10 else 1)
    scale = record['scale_to_meters']*unit_scale; ground = record['ground_source_y']
    def point(p): return Vector((p[0]*scale, -p[2]*scale, (p[1]-ground)*scale))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for side in ('l', 'r'):
        for i, base in enumerate(CHAIN):
            name = base+'_'+side
            b = rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name)
            a = point(record['joints_source'][name])
            z = point(record['joints_source'][CHAIN[i+1]+'_'+side]) if i+1 < len(CHAIN) else point(record['bone_tips_source'][name])
            along = (z-a).normalized(); across = Vector((1, 0, 0))
            across = (across-along*across.dot(along)).normalized()
            frame = Matrix((across, along, across.cross(along))).transposed().to_4x4()
            frame.translation = a
            b.matrix = frame; b.length = (z-a).length
            b.use_deform = True; b.use_connect = False
        for i, base in enumerate(CHAIN):
            b = rig.data.edit_bones[base+'_'+side]
            b.parent = rig.data.edit_bones[CHAIN[i-1]+'_'+side if i else 'pelvis']
    bpy.ops.object.mode_set(mode='OBJECT')
    for side in ('l', 'r'):
        for base in CHAIN:
            p = rig.pose.bones[base+'_'+side]
            p.rotation_mode = 'QUATERNION'; p.matrix_basis = Matrix.Identity(4)
    return record


def make_weights(rig_guides, output_path=None, region_path=None):
    """Production field on original vertex IDs; root merges only these rows.

    Feet have coherent heel/midfoot and toe-pad support; the knee/hock/ankle
    get distinct finite blend rings. No opposite limb or gill bone is allowed.
    """
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    raw = source['positions'].astype(np.float64)
    faces = source['indices'].reshape(-1, 3)
    region_path = Path(region_path or ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    labels = np.load(region_path)['face_labels']
    body_ids = np.unique(faces[labels == 0])
    guide = json.loads(Path(rig_guides).read_text(encoding='utf-8'))
    head = {n: np.asarray(v) for n, v in guide['bone_heads_cm'].items()}
    tail = {n: np.asarray(v) for n, v in guide['bone_tails_cm'].items()}
    scale = 310/(raw[:, 1].max()-raw[:, 1].min())
    points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-raw[:, 1].min()]*scale
    names = ['pelvis']+[n+'_'+side for side in ('l', 'r') for n in CHAIN]
    rows = []; values = []
    for side, sign in (('l', 1), ('r', -1)):
        ids = body_ids[(raw[body_ids, 0]*sign > .004) & (raw[body_ids, 1] < -.123)]
        q = points[ids]
        segments = []
        for i, n in enumerate(CHAIN):
            a = head[n+'_'+side]; b = head[CHAIN[i+1]+'_'+side] if i+1 < len(CHAIN) else tail[n+'_'+side]
            length = np.linalg.norm(b-a)
            t = np.clip((q-a)@(b-a)/max(length*length, 1.e-12), 0., 1.)
            d = np.linalg.norm(q-a-t[:, None]*(b-a), axis=1)
            segments.append((length, t, d))
        choice = np.argmin(np.stack([v[2] for v in segments], axis=1), axis=1)
        lengths = np.asarray([v[0] for v in segments]); knots = np.r_[0., np.cumsum(lengths)]
        arc = np.empty(len(ids))
        for i, (_, t, _) in enumerate(segments):
            selected = choice == i; arc[selected] = knots[i]+t[selected]*lengths[i]
        weights = np.zeros((len(ids), len(names)), dtype=np.float32)
        offset = 1+(0 if side == 'l' else 5)
        weights[np.arange(len(ids)), offset+choice] = 1.
        # Independent joint zones prevent diffuse weights spanning an entire
        # calf or opposite lower limb when source surfaces happen to be near.
        for i, halfwidth in ((1, 6.), (2, 5.), (3, 4.5), (4, 5.)):
            selected = np.abs(arc-knots[i]) < halfwidth
            alpha = smooth((arc[selected]-knots[i]+halfwidth)/(2*halfwidth))
            weights[selected] = 0
            weights[selected, offset+i-1] = 1-alpha
            weights[selected, offset+i] = alpha
        # Generated toes fan out sideways. Their common support may be nearer
        # the ankle line; explicitly retain a shared pad instead of nearest-bone
        # weighting curling its unrelated corners around calf/hock joints.
        foot_pad = (raw[ids, 1] < -.711) & (raw[ids, 2] > .010)
        alpha = smooth((raw[ids[foot_pad], 2]-.010)/.070)
        weights[foot_pad] = 0
        weights[foot_pad, offset+3] = 1-alpha
        weights[foot_pad, offset+4] = alpha
        heel = (raw[ids, 1] < -.702) & (raw[ids, 2] <= .010)
        weights[heel] = 0; weights[heel, offset+3] = 1
        hip = smooth((-.123-raw[ids, 1])/.077)
        weights *= hip[:, None]; weights[:, 0] = 1-hip
        rows.append(ids); values.append(weights)
    ids = np.concatenate(rows); field = np.concatenate(values)
    nonzero = np.argsort(-field, axis=1)[:, :4]
    sparse = np.take_along_axis(field, nonzero, axis=1)
    sparse /= sparse.sum(axis=1, keepdims=True)
    output_path = Path(output_path or OUT/'leg_weights_v07.npz')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, source_vertex_ids=ids.astype(np.int32), bone_names=np.asarray(names),
        bone_indices=nonzero.astype(np.int16), weights=sparse.astype(np.float32))
    write_json(output_path.with_suffix('.json'), {'revision': 'OriginalV07', 'source_vertex_rows': len(ids),
        'source_mesh': str(ROOT/'Authoring/source_mesh.npz'), 'rig_guides': str(rig_guides),
        'bone_names': names, 'maximum_influences': 4,
        'joint_blend_halfwidth_cm': {'knee': 6, 'hock': 5, 'ankle': 4.5, 'forefoot': 5},
        'pelvis_attachment_source_y': [-.123, -.200], 'method': 'Source-side anatomical chain, coherent ankle/heel/pad fields, normalized finite joint rings; non-leg source rows are not replaced.',
        'tested': False, 'rendered': False})
    return str(output_path)


def _cubic(curve, phase):
    values = np.asarray(curve, dtype=np.float64)
    at = (phase % 1.)*len(values); i = int(math.floor(at)); t = at-i
    a, b, c, d = [values[(i+k) % len(values)] for k in (-1, 0, 1, 2)]
    return .5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)


def _control(data, phase, duty, speed_m_s, duration, lift_m):
    phase %= 1.
    start = data['stance_start_phase']; end = data['stance_end_phase']
    foot = data['foot_head_m']; source_floor = data['source_contact_floor_m']
    if phase < duty:
        source_phase = start+(end-start)*phase/duty
        y = speed_m_s*duration*(phase-duty*.5)
        z = 0.; contact = float(smooth(min(phase/.04, (duty-phase)/.04)))
    else:
        t = (phase-duty)/(1.-duty)
        source_phase = end+(start+1.-end)*t
        sample = _cubic(foot, source_phase)
        a = _cubic(foot, end); b = _cubic(foot, start+1.)
        yspan = b[1]-a[1]
        progress = (sample[1]-a[1])/yspan if abs(yspan) > .02 else float(smooth(t))
        # Retain smoothed source fore/aft recovery timing; keep its endpoint
        # exactly on the biped stance path. A small quintic blend keeps lift-off
        # and landing attached to their contact position.
        progress = .70*float(np.clip(progress, 0, 1))+.30*float(smooth(t))
        span = speed_m_s*duration*duty
        tangent = speed_m_s*duration*(1.-duty)
        # Stance retreats at the authorized navigation speed. Hermite recovery
        # retains that derivative at both borders; source-shape offsets fade
        # with zero derivative there, so the ankle never changes speed abruptly.
        y = (.5*span)*(2*t**3-3*t*t+1)+tangent*(t**3-2*t*t+t)+(-.5*span)*(-2*t**3+3*t*t)+tangent*(t**3-t*t)
        y += .18*span*(float(smooth(t))-progress)*math.sin(math.pi*t)**2
        zrange = max(np.max(np.asarray(foot)[:, 2])-source_floor, .001)
        envelope = float(smooth(t/.14)*smooth((1.-t)/.16))
        z = lift_m*max(0., float(sample[2]-source_floor))/zrange*envelope
        contact = 0.
    angle = float(_cubic(data['hock_sagittal_angle'], source_phase))-data['hock_sagittal_angle_mean']
    return y, z, contact, float(np.clip(angle, -math.radians(22), math.radians(22)))


def apply_motion(rig, action, name, fps=30, unit_scale=None):
    """Bake an existing action's legs on its complete V07 reference.

    Call after existing twelve-action choreography and BEFORE FBX export. This
    is curve production, not playback, a runtime test or visual acceptance.
    Durations, hit times, torso/arm choreography and AI contracts are retained.
    """
    import bpy
    from mathutils import Vector, Matrix, Quaternion
    role = name.removeprefix('A_M07_')
    unit_scale = unit_scale or (100 if rig.data.bones['pelvis'].head_local.z > 10 else 1)
    data = json.loads((OUT/'canine_hindleg_controls_v07.json').read_text(encoding='utf-8'))
    rig.animation_data_create(); rig.animation_data.action = action
    if action.slots: rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks: track.mute = True
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    keys = [base+'_'+side for side in ('l', 'r') for base in CHAIN]
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    curves = action.fcurves if not action.is_action_layered else [c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]
    # The reference-only frame 0 is outside every source action. All other
    # production keys keep the original source interval exactly.
    endpoints = [float(k.co.x) for c in curves for k in c.keyframe_points if k.co.x >= 1]
    start = 1; end = int(round(max(endpoints))); duration = (end-start)/fps
    locomotion = role in ('SlowWalk', 'Chase')
    speed = (.90 if role == 'SlowWalk' else 1.45) if locomotion else 0.
    duty = .68 if role == 'SlowWalk' else .60
    floor_actions = ('Idle', 'WallListen', 'MeleeLeft', 'MeleeRight', 'Hit', 'Dizzy')
    produced = []; previous = {}

    def frame_for(n, head, direction):
        reference = (rig.data.bones[n].tail_local-rig.data.bones[n].head_local).normalized()
        q = reference.rotation_difference(direction.normalized())@rest[n].to_quaternion()
        matrix = q.to_matrix().to_4x4(); matrix.translation = head
        return matrix

    for frame in range(start, end+1):
        bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
        target = {p.name: p.matrix.copy() for p in ordered}
        phase = (frame-start)/max(end-start, 1)
        qpelvis = target['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
        controls_by_side = {side: _control(data, phase+(0 if side == 'l' else .5), duty, speed,
            duration, .14 if role == 'SlowWalk' else .21) for side in ('l', 'r')}
        if locomotion:
            # Horizontal centre follows the supporting side; shared vertical
            # crouch supplies three-link flexion reserve at full stride.
            contrast = controls_by_side['l'][2]-controls_by_side['r'][2]
            desired = rest['pelvis'].translation+Vector((contrast*.045*unit_scale,
                0., (-.11 if role == 'SlowWalk' else -.14)*unit_scale+.012*unit_scale*math.cos(4*math.pi*phase)))
            delta = desired-target['pelvis'].translation
            for matrix in target.values(): matrix.translation += delta
        for side, sign in (('l', 1), ('r', -1)):
            ns = [base+'_'+side for base in CHAIN]
            hip = target[ns[0]].translation.copy()
            lengths = [(rest[ns[i+1]].translation-rest[ns[i]].translation).length for i in range(3)]
            a, b, c = lengths
            if locomotion:
                y, z, contact, hock_angle = controls_by_side[side]
                toe = rest[ns[4]].translation+Vector((0, y*unit_scale, z*unit_scale))
                sagittal = math.atan2((rest[ns[3]].translation-rest[ns[2]].translation).y,
                    -(rest[ns[3]].translation-rest[ns[2]].translation).z)+hock_angle
                preferred = Vector((0, math.sin(sagittal), -math.cos(sagittal))).normalized()
                swing_phase = ((phase+(0 if side == 'l' else .5)) % 1.-duty)/(1.-duty)
                # Forefoot stays level while supporting. Swing folds the toes
                # from the ankle; it does not translate phalanges independently.
                pitch = math.radians(14)*math.sin(math.pi*max(0., swing_phase)) if not contact else 0.
                foot_q = Quaternion((1, 0, 0), pitch)@rest[ns[3]].to_quaternion()
            elif role in floor_actions:
                toe = rest[ns[4]].translation.copy()
                if role == 'Hit': toe = toe.lerp(target[ns[4]].translation, .25)
                foot_q = rest[ns[3]].to_quaternion()
                preferred = (rest[ns[3]].translation-rest[ns[2]].translation).normalized()
                contact = 1.
            else:
                # Keep authored falling/get-up intent and its actual foot goal;
                # the new hock follows pelvis tilt without snapping to upright.
                toe = target[ns[4]].translation.copy()
                foot_q = target[ns[3]].to_quaternion()
                preferred = qpelvis@(rest[ns[3]].translation-rest[ns[2]].translation).normalized()
                contact = 0.
            paw = rest[ns[3]].to_quaternion().inverted()@(rest[ns[4]].translation-rest[ns[3]].translation)
            ankle_goal = toe-foot_q@paw
            axis = ankle_goal-hip
            if axis.length < .00001: axis = Vector((0, 0, -1))
            distance = axis.length; axis.normalize()
            # Explicit hock preference followed by proximal two-link solve,
            # as NaturalV3. Neither knee nor hock is left to free FABRIK flips.
            proximal = math.sqrt(a*a+b*b+2*a*b*math.cos(math.radians(14)))
            distance = min(distance, proximal+c-.001*unit_scale)
            fitted = hip+axis*distance
            hock = fitted-preferred*c
            reach = (hock-hip).length; width = .035*unit_scale
            easing = max(0., width-abs(reach-proximal))/max(width, .000001)
            minimum = max(abs(a-b)+.00001*unit_scale, abs(distance-c)+.00001*unit_scale)
            maximum = min(proximal, distance+c-.00001*unit_scale)
            softened = max(minimum, min(maximum, min(reach, proximal)-easing*easing*width*.25))
            if abs(reach-softened) > .000001:
                along = (softened*softened-c*c+distance*distance)/(2*distance)
                radius = math.sqrt(max(0., softened*softened-along*along))
                center = hip+axis*along; offset = hock-center; offset -= axis*offset.dot(axis)
                if offset.length < .000001:
                    offset = Vector((0, 1, 0)); offset -= axis*offset.dot(axis)
                hock = center+offset.normalized()*radius
            direction = hock-hip; reach = direction.length; direction.normalize()
            # Keep original upper-knee plane; source dog's knee points forward,
            # hock backward. Plane is transported during falls and recovery.
            pole = Vector((0, -1, 0)) if locomotion or role in floor_actions else qpelvis@Vector((0, -1, 0))
            pole -= direction*pole.dot(direction)
            if pole.length < .000001: pole = Vector((sign, 0, 0))
            pole.normalize()
            reach = max(abs(a-b)+.00001*unit_scale, min(reach, proximal))
            along = (a*a-b*b+reach*reach)/(2*reach)
            knee = hip+direction*along+pole*math.sqrt(max(0., a*a-along*along))
            hock = hip+direction*reach
            target[ns[0]] = frame_for(ns[0], hip, knee-hip)
            target[ns[1]] = frame_for(ns[1], knee, hock-knee)
            target[ns[2]] = frame_for(ns[2], hock, fitted-hock)
            target[ns[3]] = foot_q.to_matrix().to_4x4(); target[ns[3]].translation = fitted
            delta = foot_q@rest[ns[3]].to_quaternion().inverted()
            target[ns[4]] = (delta@rest[ns[4]].to_quaternion()).to_matrix().to_4x4()
            target[ns[4]].translation = fitted+foot_q@paw
        write_names = (['pelvis'] if locomotion else [])+keys
        for p in ordered:
            if p.name not in write_names: continue
            if p.parent:
                p.matrix_basis = p.bone.convert_local_to_pose(target[p.name], p.bone.matrix_local,
                    parent_matrix=target[p.parent.name], parent_matrix_local=p.parent.bone.matrix_local, invert=True)
            else:
                p.matrix_basis = p.bone.convert_local_to_pose(target[p.name], p.bone.matrix_local, invert=True)
            p.rotation_mode = 'QUATERNION'
            if p.name in keys:
                p.location = Vector(); p.scale = Vector((1, 1, 1))
            q = p.rotation_quaternion.copy()
            if p.name in previous and q.dot(previous[p.name]) < 0:
                q.negate(); p.rotation_quaternion = q
            previous[p.name] = q
            for prop in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=prop, frame=frame, group=p.name)
        produced.append({'frame': frame, 'phase': phase,
            'contacts': {s: float(controls_by_side[s][2]) if locomotion else float(role in floor_actions) for s in ('l', 'r')}})
    # Reference frame and loop endpoints remain completely compatible with the
    # source mesh and all other thirteen-state runtime transitions.
    for n in keys:
        p = rig.pose.bones[n]; p.matrix_basis = Matrix.Identity(4)
        for prop in ('location', 'rotation_quaternion', 'scale'):
            p.keyframe_insert(data_path=prop, frame=0, group=p.name)
    final_curves = action.fcurves if not action.is_action_layered else [c for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]
    for curve in final_curves:
        if any(curve.data_path.startswith('pose.bones["'+n+'"]') for n in keys+(['pelvis'] if locomotion else [])):
            for k in curve.keyframe_points: k.interpolation = 'LINEAR'
    record = {'action': action.name, 'role': role, 'fps': fps, 'frames': end, 'duration_seconds': duration,
        'biped_phase_offset': .5, 'source': str(SOURCE), 'leg_bones': keys,
        'source_control_recipe': 'NaturalV3 cyclic 5-tap smoothing and Catmull interpolation before support constraints; explicit posterior hock and forward knee planes',
        'speed_cm_s': speed*100, 'stance_fraction': duty if locomotion else None,
        'frames_authored': produced, 'tested': False, 'rendered': False, 'runtime_sampled': False}
    write_json(OUT/'actions'/f'{role}_hindleg_authoring.json', record)
    bpy.context.scene.frame_set(0)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rig-guides')
    parser.add_argument('--regions')
    args = parser.parse_args()
    record = anatomy(args.regions)
    if args.rig_guides:
        print(make_weights(args.rig_guides, region_path=args.regions))
    else:
        # Numeric reference is authored directly from the same source guides
        # consumed by apply_reference. It is not an exported or tested rig.
        base = json.loads((ROOT/'RecoveryOriginalV06/rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))
        scale = record['scale_to_meters']*100; ground = record['ground_source_y']
        def cm(p): return [p[0]*scale, -p[2]*scale, (p[1]-ground)*scale]
        head = {n: cm(p) for n, p in record['joints_source'].items()}
        head['pelvis'] = base['bone_heads_cm']['pelvis']
        tail = {}
        for side in ('l', 'r'):
            for i, n in enumerate(CHAIN):
                tail[n+'_'+side] = head[CHAIN[i+1]+'_'+side] if i+1 < len(CHAIN) else cm(record['bone_tips_source'][n+'_'+side])
        tail['pelvis'] = base['bone_tails_cm']['pelvis']
        numeric = OUT/'hindleg_weight_reference_cm_v07.json'
        write_json(numeric, {'bone_heads_cm': head, 'bone_tails_cm': tail,
            'reference_source': str(OUT/'hindleg_anatomy_v07.json'), 'actual_rig_export': False})
        print(make_weights(numeric, region_path=args.regions))
    print('M07_ORIGINAL_V07_HINDLEG_SOURCE_SAVED '+str(OUT/'hindleg_anatomy_v07.json'))
