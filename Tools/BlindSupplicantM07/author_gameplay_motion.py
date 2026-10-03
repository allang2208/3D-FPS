"""Author M07's body clips on its retained, separately authored skeleton.

The source gait is read from the actual Nurse anatomical donor. Joint-local
rotations are transferred in the donor-derived target rest frames, while foot
endpoints are solved on M07's own limb lengths. No render, cloth evaluation,
gameplay test or source/master replacement is performed by this authoring tool.
"""
import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'Motion'
DONOR = ROOT.parent / 'WitchMeshy20260919/Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx'
MASTER = ROOT / 'Authoring/M07_Separated_Master.blend'
FPS = 30


def update():
    bpy.context.view_layer.update()


def rows(m):
    return [[float(x) for x in row] for row in m]


def read_source():
    """Read animation and coordinate data needed to adapt the donor gait."""
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(DONOR), use_anim=True)
    r = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    a = r.animation_data.action
    start, end = a.frame_range
    srcfps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    count = round((end - start) / srcfps * FPS) + 1
    rest = {b.name: rows(r.matrix_world @ b.matrix_local) for b in r.data.bones}
    samples = []
    for i in range(count):
        f = start + i * srcfps / FPS
        bpy.context.scene.frame_set(math.floor(f), subframe=f % 1)
        samples.append({
            'world': {b.name: rows(r.matrix_world @ b.matrix) for b in r.pose.bones},
            'basis': {b.name: rows(b.matrix_basis) for b in r.pose.bones},
        })
    result = {
        'source': str(DONOR), 'action': a.name,
        'source_fps': srcfps, 'source_start': float(start), 'source_end': float(end),
        'fps': FPS, 'duration': (count - 1) / FPS, 'frames': count,
        'object_matrix_world': rows(r.matrix_world), 'rest': rest,
        'parents': {b.name: b.parent.name if b.parent else None for b in r.data.bones},
        'samples': samples,
    }
    (OUT / 'nurse_source_motion.json').write_text(json.dumps(result), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('action', 'source_fps', 'source_start', 'source_end', 'duration', 'frames')}), flush=True)
    print(json.dumps({'source_object_matrix': result['object_matrix_world'],
                      'source_pelvis_rest': rest['pelvis'],
                      'source_pelvis_first_basis': samples[0]['basis']['pelvis'],
                      'source_bones': list(rest)}), flush=True)
    return result


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def ramp(t, a, b):
    return smooth((t - a) / (b - a))


def world(r, n):
    return r.matrix_world @ r.pose.bones[n].matrix


def put(r, n, m):
    r.pose.bones[n].matrix = r.matrix_world.inverted() @ m
    update()


def rotate(r, n, axis, degrees):
    m = world(r, n)
    q = Quaternion(Vector(axis), math.radians(degrees))
    put(r, n, Matrix.LocRotScale(m.translation, q @ m.to_quaternion(), Vector((1, 1, 1))))


def solve(r, upper, lower, end, endpoint, pole):
    """Two-segment IK keeps target segment lengths and articulated endpoints."""
    a, b, c = [world(r, n) for n in (upper, lower, end)]
    p = a.translation.copy()
    l1 = (b.translation - p).length
    l2 = (c.translation - b.translation).length
    d = endpoint.translation - p
    distance = max(abs(l1 - l2) + .006, min(d.length, l1 + l2 - .006))
    direction = d.normalized()
    knee = pole - p
    knee -= direction * knee.dot(direction)
    if knee.length < .001:
        knee = Vector((0, -1, 0))
        knee -= direction * knee.dot(direction)
    knee.normalize()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    bend = p + direction * along + knee * math.sqrt(max(0, l1 * l1 - along * along))
    q = (b.translation - p).rotation_difference(bend - p)
    put(r, upper, Matrix.LocRotScale(p, q @ a.to_quaternion(), Vector((1, 1, 1))))
    b, c = world(r, lower), world(r, end)
    q = (c.translation - b.translation).rotation_difference(endpoint.translation - b.translation)
    put(r, lower, Matrix.LocRotScale(b.translation, q @ b.to_quaternion(), Vector((1, 1, 1))))
    # Clamp an unreachable endpoint onto the target skeleton's physical reach;
    # never stretch a limb to satisfy a trajectory authored for another body.
    c = world(r, end)
    put(r, end, Matrix.LocRotScale(c.translation, endpoint.to_quaternion(), Vector((1, 1, 1))))


def mix_matrix(a, b, amount):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, amount),
                             a.to_quaternion().slerp(b.to_quaternion(), amount),
                             Vector((1, 1, 1)))


def sample_source(src, phase):
    index = max(0.0, min(1.0, phase)) * (len(src['samples']) - 1)
    lo = int(index)
    hi = min(lo + 1, len(src['samples']) - 1)
    amount = index - lo
    return {
        kind: {n: mix_matrix(Matrix(src['samples'][lo][kind][n]),
                            Matrix(src['samples'][hi][kind][n]), amount)
               for n in src['rest']}
        for kind in ('world', 'basis')
    }


def authored_finger_relax(r, strength):
    """A small anatomical bend toward each hand's palm, retaining five fingers."""
    for side in ('l', 'r'):
        hand = world(r, 'hand_' + side)
        index = world(r, 'index_01_' + side).translation - hand.translation
        pinky = world(r, 'pinky_01_' + side).translation - hand.translation
        normal = index.cross(pinky).normalized()
        # Orient palm closure into the inside of the retained hand, consistently
        # across mirrored donor frames rather than copying Euler signs.
        if normal.dot(hand.to_3x3() @ Vector((0, 0, 1))) < 0:
            normal.negate()
        for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            for j in range(1, 4):
                n = f'{finger}_{j:02d}_{side}'
                if n not in r.pose.bones:
                    continue
                b = r.pose.bones[n]
                direction = (world(r, n).to_3x3() @ Vector((0, 1, 0))).normalized()
                axis = direction.cross(normal)
                if axis.length < .001:
                    continue
                axis.normalize()
                degrees = ((3 + j * 2) if finger == 'thumb' else (6 + j * 3)) * strength
                rotate(r, n, axis, degrees)


def author():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / 'nurse_source_motion.json'
    src = json.loads(cache.read_text()) if cache.exists() else read_source()
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    r = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    r.animation_data_clear()
    r.data.pose_position = 'POSE'
    r.matrix_world = Matrix.Identity(4)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1
    # Only armature evaluation is required to author clips. The retained million
    # face display, Surface Deform bindings and disabled cloth settings remain
    # untouched in the saved source, without evaluating cloth or display meshes.
    visibility = []
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for m in o.modifiers:
                visibility.append((m, m.show_viewport, m.show_render))
                m.show_viewport = False
                m.show_render = False
    for b in r.pose.bones:
        b.rotation_mode = 'QUATERNION'
        b.matrix_basis = Matrix.Identity(4)
    update()
    rest = {b.name: world(r, b.name).copy() for b in r.pose.bones}
    src_rest = {n: Matrix(m) for n, m in src['rest'].items()}
    first = {kind: {n: Matrix(m) for n, m in src['samples'][0][kind].items()}
             for kind in ('world', 'basis')}
    last = {kind: {n: Matrix(m) for n, m in src['samples'][-1][kind].items()}
            for kind in ('world', 'basis')}
    legscale = sum((rest['thigh_' + s].translation - rest['calf_' + s].translation).length +
                   (rest['calf_' + s].translation - rest['foot_' + s].translation).length
                   for s in ('l', 'r')) / sum(
        (src_rest['thigh_' + s].translation - src_rest['calf_' + s].translation).length +
        (src_rest['calf_' + s].translation - src_rest['foot_' + s].translation).length
        for s in ('l', 'r'))
    gait_lows = {s: min(Matrix(f['world']['foot_' + s]).translation.z
                        for f in src['samples']) for s in ('l', 'r')}
    pelvis_mean_z = sum(Matrix(f['world']['pelvis']).translation.z for f in src['samples']) / len(src['samples'])
    hand_neutral = {}
    arm_length = {}
    for s, sign in (('l', 1), ('r', -1)):
        shoulder = rest['upperarm_' + s].translation
        arm_length[s] = (rest['lowerarm_' + s].translation - shoulder).length + \
                        (rest['hand_' + s].translation - rest['lowerarm_' + s].translation).length
        # Rest-frame correction rotates the complete arm/hand basis from M07's
        # spread binding frame toward the same anatomical hanging direction.
        direction = Vector((sign * .035, -.07, -1)).normalized()
        align = (rest['hand_' + s].translation - shoulder).rotation_difference(direction)
        hand_neutral[s] = Matrix.LocRotScale(
            shoulder + direction * arm_length[s] * .93,
            align @ rest['hand_' + s].to_quaternion(), Vector((1, 1, 1)))
    clips = [
        ('Idle', 4.0, True, None),
        ('SlowWalk', 3.3, True, None),
        ('Chase', 1.5, True, None),
        ('MeleeLeft', 1.5, False, .68),
        ('MeleeRight', 1.65, False, .78),
        ('Hit', .9, False, None),
        ('Death', 2.4, False, None),
        ('WallListen', 3.2, False, None),
    ]
    manifest = {
        'schema': 1, 'character': 'BlindSupplicantM07', 'fps': FPS,
        'master_source': str(MASTER), 'gameplay_source': str(OUT / 'M07_GameplayMotion.blend'),
        'source_gait': {k: src[k] for k in ('source', 'action', 'source_start', 'source_end', 'duration', 'frames')},
        'rest_adaptation': {
            'method': 'Actual donor rest/local rotation data; M07 metre-scale rest frames; target-length two-segment IK; source object 0.01 scale removed exactly once.',
            'source_object_matrix_world': src['object_matrix_world'],
            'target_rest_world_m': {n: rows(m) for n, m in rest.items()},
            'source_rest_world_m': src['rest'],
            'leg_length_ratio': legscale,
            'arm_length_m': arm_length,
            'all_body_and_gill_bones': list(rest),
        },
        'import': {'fps': FPS, 'axis_forward': '-Y', 'axis_up': 'Z',
                   'blender_scale_length': scene.unit_settings.scale_length,
                   'apply_unit_scale': True, 'apply_scale_options': 'FBX_SCALE_UNITS',
                   'ue_convert_scene': True, 'ue_convert_scene_unit': True,
                   'ue_import_uniform_scale': 1.0, 'ue_preserve_local_transform': True,
                   'ue_use_default_sample_rate': True, 'ue_import_mesh': False,
                   'ue_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_Skeleton'},
        'clips': {}, 'tested': False, 'rendered': False,
        'cloth_simulation_played': False,
        'assumptions': [
            'SlowWalk reuses the retained Nurse gait; Chase is an accelerated and slightly lengthened gait, not a separate running mocap source.',
            'Standing, finger relaxation, alternating deliberate long-arm sweeps, hit, death and wall-listening are original M07 choreography.',
            'Melee impact times are gameplay authoring contracts, not visually accepted collision contacts.',
            'The master skin/semantic cuts remain the current production pass; no render or gameplay validation is performed.',
        ],
    }
    actions = {}
    for role, duration, loop, impact in clips:
        count = round(duration * FPS) + 1
        duration = (count - 1) / FPS
        scene.frame_start = 1
        scene.frame_end = count
        action = bpy.data.actions.new('A_M07_' + role)
        action.use_fake_user = True
        r.animation_data_create()
        r.animation_data.action = action
        actions[role] = action
        feet = {s: [] for s in ('l', 'r')}
        for i in range(count):
            t, u = i / FPS, i / (count - 1)
            scene.frame_set(i + 1)
            for b in r.pose.bones:
                b.matrix_basis = Matrix.Identity(4)
            update()
            pelvis = rest['pelvis'].copy()
            pelvis.translation += Vector((.006 * math.sin(2 * math.pi * u), 0, -.018))
            put(r, 'pelvis', pelvis)
            torso_wave = math.sin(2 * math.pi * u)
            for n, degree in (('spine_02', 2.5), ('spine_04', 4), ('neck_01', 6), ('head', 8)):
                rotate(r, n, (1, 0, 0), degree + .6 * torso_wave)
            endpoint = {s: rest['foot_' + s].copy() for s in ('l', 'r')}
            hands = {s: hand_neutral[s].copy() for s in ('l', 'r')}
            finger_strength = .45
            if role in ('SlowWalk', 'Chase'):
                sample = sample_source(src, u)
                # The donor travels -Y. Removing each track's endpoint drift
                # produces a genuinely in-place cycle on M07's own lengths.
                gait_strength = .82 if role == 'SlowWalk' else 1.0
                p = sample['world']['pelvis'].translation
                p0, p1 = first['world']['pelvis'].translation, last['world']['pelvis'].translation
                sway = p - p0.lerp(p1, u)
                pelvis = rest['pelvis'].copy()
                pelvis.translation += Vector((sway.x * legscale * .55,
                                              sway.y * legscale * .10,
                                              (p.z - pelvis_mean_z) * legscale - .025))
                put(r, 'pelvis', pelvis)
                q = first['basis']['pelvis'].to_quaternion().inverted() @ sample['basis']['pelvis'].to_quaternion()
                endq = first['basis']['pelvis'].to_quaternion().inverted() @ last['basis']['pelvis'].to_quaternion()
                q = q @ Quaternion().slerp(endq, u).inverted()
                r.pose.bones['pelvis'].rotation_quaternion = r.pose.bones['pelvis'].rotation_quaternion @ Quaternion().slerp(q, .45)
                update()
                for n in ('spine_02', 'spine_04', 'neck_01', 'head'):
                    if n in sample['basis']:
                        q = first['basis'][n].to_quaternion().inverted() @ sample['basis'][n].to_quaternion()
                        endq = first['basis'][n].to_quaternion().inverted() @ last['basis'][n].to_quaternion()
                        q = q @ Quaternion().slerp(endq, u).inverted()
                        r.pose.bones[n].rotation_quaternion = r.pose.bones[n].rotation_quaternion @ Quaternion().slerp(q, .35)
                update()
                for s, sign in (('l', 1), ('r', -1)):
                    name = 'foot_' + s
                    p = sample['world'][name].translation
                    p0, p1 = first['world'][name].translation, last['world'][name].translation
                    displacement = p - p0.lerp(p1, u)
                    endpoint[s].translation.x += displacement.x * legscale * .45
                    endpoint[s].translation.y += displacement.y * legscale * gait_strength
                    # Keep real donor swing height while preserving the target
                    # ankle-to-ground offset and the same endpoint at loop wrap.
                    swing = max(0.0, p.z - gait_lows[s] - u * (p1.z - p0.z))
                    endpoint[s].translation.z += swing * legscale * .80
                    q = (sample['world'][name].to_quaternion() @ first['world'][name].to_quaternion().inverted())
                    endq = last['world'][name].to_quaternion() @ first['world'][name].to_quaternion().inverted()
                    q = q @ Quaternion().slerp(endq, u).inverted()
                    endpoint[s] = Matrix.LocRotScale(endpoint[s].translation,
                                                     Quaternion().slerp(q, .55) @ endpoint[s].to_quaternion(),
                                                     Vector((1, 1, 1)))
                    hands[s].translation += Vector((sign * .015 * torso_wave,
                                                     -.08 * math.sin(2 * math.pi * u + (0 if s == 'l' else math.pi)),
                                                     .015 * torso_wave))
            elif role in ('MeleeLeft', 'MeleeRight'):
                s = 'l' if role == 'MeleeLeft' else 'r'
                sign = 1 if s == 'l' else -1
                wind = ramp(t, .08, impact - .22)
                hit = ramp(t, impact - .22, impact)
                recover = ramp(t, impact + .18, duration)
                shoulder = world(r, 'upperarm_' + s).translation
                windm = hands[s].copy()
                windm.translation = Vector((sign * .91, .14, 1.85))
                strike = hands[s].copy()
                strike.translation = Vector((sign * .08, -1.20, 1.53))
                strike_q = Quaternion((1, 0, 0), math.radians(18)) @ hands[s].to_quaternion()
                strike = Matrix.LocRotScale(strike.translation, strike_q, Vector((1, 1, 1)))
                attack_hand = mix_matrix(hands[s], windm, wind)
                attack_hand = mix_matrix(attack_hand, strike, hit)
                hands[s] = mix_matrix(attack_hand, hand_neutral[s], recover)
                lean = hit * (1 - recover)
                rotate(r, 'spine_03', (0, 0, 1), sign * (9 * wind - 21 * hit) * (1 - recover))
                rotate(r, 'spine_04', (1, 0, 0), 7 * lean)
                pelvis = world(r, 'pelvis')
                pelvis.translation += Vector((0, -.055 * lean, -.025 * wind * (1 - recover)))
                put(r, 'pelvis', pelvis)
                hands['r' if s == 'l' else 'l'].translation.y += .08 * lean
                finger_strength = .45 + .8 * wind * (1 - recover)
            elif role == 'Hit':
                recoil = ramp(t, 0, .16) * (1 - ramp(t, .3, duration))
                rotate(r, 'spine_02', (1, 0, 0), -7 * recoil)
                rotate(r, 'spine_04', (1, 0, 0), -9 * recoil)
                rotate(r, 'head', (0, 0, 1), 7 * recoil)
                pelvis = world(r, 'pelvis')
                pelvis.translation += Vector((0, .035, -.045)) * recoil
                put(r, 'pelvis', pelvis)
                for s, sign in (('l', 1), ('r', -1)):
                    hands[s].translation += Vector((sign * .10, -.08, .16)) * recoil
            elif role == 'Death':
                sink = ramp(t, .08, .75)
                fall = ramp(t, .45, duration)
                pelvis = world(r, 'pelvis')
                pelvis.translation += Vector((.035 * fall, .60 * fall, -.22 * sink - .78 * fall))
                q = Quaternion((1, 0, 0), math.radians(-82 * fall))
                pelvis = Matrix.LocRotScale(pelvis.translation, q @ pelvis.to_quaternion(), Vector((1, 1, 1)))
                put(r, 'pelvis', pelvis)
                rotate(r, 'spine_04', (1, 0, 0), -9 * fall)
                for s, sign in (('l', 1), ('r', -1)):
                    endpoint[s].translation += Vector((sign * .055 * fall, -.08 * fall,
                                                        .015 * ramp(t, 1.25, duration)))
                    hands[s].translation = hand_neutral[s].translation.lerp(
                        Vector((sign * .55, .71, .22)), fall)
                finger_strength = .45 * (1 - fall)
            elif role == 'WallListen':
                listen = ramp(t, .15, .85) * (1 - ramp(t, 2.35, duration))
                rotate(r, 'spine_03', (1, 0, 0), 7 * listen)
                rotate(r, 'neck_02', (0, 0, 1), 28 * listen)
                rotate(r, 'head', (0, 1, 0), -8 * listen)
                reach = hands['l'].copy()
                reach.translation = Vector((.20, -.65, 2.0))
                reach = Matrix.LocRotScale(reach.translation,
                                          Quaternion((1, 0, 0), math.radians(-65)) @ reach.to_quaternion(),
                                          Vector((1, 1, 1)))
                hands['l'] = mix_matrix(hands['l'], reach, listen)
                hands['r'].translation.y += .065 * listen
            # Foot anchors and M07-length limbs are solved on every authored
            # body pose, so torso gesture transfer never scales/tears anatomy.
            for s, sign in (('l', 1), ('r', -1)):
                knee = world(r, 'thigh_' + s).translation + Vector((sign * .02, -.65, -.35))
                solve(r, 'thigh_' + s, 'calf_' + s, 'foot_' + s, endpoint[s], knee)
                shoulder = world(r, 'upperarm_' + s).translation
                elbow = shoulder + Vector((sign * .26, .22, -.72))
                solve(r, 'upperarm_' + s, 'lowerarm_' + s, 'hand_' + s, hands[s], elbow)
                feet[s].append(world(r, 'ball_' + s).translation.copy())
            authored_finger_relax(r, finger_strength)
            gilltime = u if loop else t / 4.0
            fade = (1 - ramp(t, .55, 1.44)) if role == 'Death' else 1.0
            for panel in range(1, 7):
                phase = -(panel - 1) * .38
                wave = math.sin(2 * math.pi * gilltime + phase) - math.sin(phase)
                for j in range(3):
                    n = f'gill_{panel:02d}_{j:02d}'
                    r.pose.bones[n].rotation_quaternion = (
                        Quaternion((1, 0, 0), math.radians((1 + j * .7) * wave * fade)) @
                        Quaternion((0, 1, 0), math.radians(.5 * wave * fade)))
            for b in r.pose.bones:
                b.keyframe_insert('location', frame=i + 1, group=b.name)
                b.keyframe_insert('rotation_quaternion', frame=i + 1, group=b.name)
                b.keyframe_insert('scale', frame=i + 1, group=b.name)
        # Original gait source carries a very small residual loop mismatch.
        # All authored looping endpoint poses, including six gill chains, are
        # explicitly identical. This is source authoring, without playback.
        if loop:
            scene.frame_set(1)
            opening = {b.name: b.matrix_basis.copy() for b in r.pose.bones}
            scene.frame_set(count)
            for b in r.pose.bones:
                b.matrix_basis = opening[b.name]
                b.keyframe_insert('location', frame=count, group=b.name)
                b.keyframe_insert('rotation_quaternion', frame=count, group=b.name)
                b.keyframe_insert('scale', frame=count, group=b.name)
        scene.frame_set(1)
        bpy.ops.object.select_all(action='DESELECT')
        r.hide_set(False)
        r.select_set(True)
        bpy.context.view_layer.objects.active = r
        path = OUT / ('A_M07_' + role + '.fbx')
        bpy.ops.export_scene.fbx(
            filepath=str(path), use_selection=True, object_types={'ARMATURE'},
            add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
            bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
            bake_anim_step=1, bake_anim_simplify_factor=0,
            axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS')
        curves = {}
        for s, positions in feet.items():
            curves['FootSpeed_' + s] = [
                (positions[min(count - 1, j + 1)] - positions[max(0, j - 1)]).length *
                100 * FPS / max(1, min(count - 1, j + 1) - max(0, j - 1))
                for j in range(count)]
        manifest['clips'][role] = {
            'file': str(path), 'asset': '/Game/Monsters/BlindSupplicantM07/Animations/A_M07_' + role,
            'action': action.name, 'frames': count, 'frame_start': 1, 'frame_end': count,
            'fps': FPS, 'duration': duration, 'loop': loop,
            'root_motion': False, 'rig_object_transform': 'Identity, static; units metres',
            'bone_tracks': list(rest), 'impact_seconds': impact,
            'impact_frame_zero_based': impact * FPS if impact is not None else None,
            'curves': curves,
            'gill_breathing': 'Six phase-offset three-bone chains; looping clips complete one breath, death fades before 60 percent ragdoll handoff.',
            'source': 'Actual Nurse anatomical donor gait; retimed and target-length adapted' if role in ('SlowWalk', 'Chase') else 'Original M07 authored choreography on retained complete anatomy',
            'death_ragdoll_seconds': duration * .6 if role == 'Death' else None,
        }
        (OUT / 'motion_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print('AUTHORED ' + role + ' -> ' + str(path), flush=True)
    r.animation_data.action = actions['Idle']
    scene.frame_start = 1
    scene.frame_end = 121
    scene.frame_set(1)
    for m, viewport, render in visibility:
        m.show_viewport = viewport
        m.show_render = render
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'M07_GameplayMotion.blend'))
    manifest['source_saved'] = True
    manifest['animation_fbx_exported'] = True
    (OUT / 'motion_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'source_saved': manifest['gameplay_source'], 'clips_exported': list(manifest['clips']), 'tested': False}), flush=True)


if __name__ == '__main__':
    import sys
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--read-source' in arguments:
        read_source()
    else:
        author()
