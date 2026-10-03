"""Author M07 sweeps and two-stage casting on the untouched V13 reference.

Rampage's actual biped melee joint/body trajectory is the sweep reference.
Its large torso turn and overhead windup are adapted to a front-facing,
long-armed humanoid; donor bone transforms, skin and meshes are not copied.
Player FireballCastMotion curves and current palm semantics are the casting
reference, with fixed third-person shoulder positions and M07 bone lengths.
This is background source production/export, without gameplay or rendering.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'CombatMagicV14/Motion'
MASTER = ROOT/'RecoveryOriginalV13/M07_Original_Recovery_V13.blend'
DONOR = PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/source_motion'
FPS = 30
UP = Vector((0, 0, 1))
FWD = Vector((0, -1, 0))
RIGHT = Vector((1, 0, 0))
CAM_TO_M07 = Matrix(((0, -1, 0), (-1, 0, 0), (0, 0, 1)))
DONOR_TO_M07 = Matrix(((1, 0, 0), (0, -1, 0), (0, 0, 1)))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
from repair_attack_arms_v13 import neutral_body_cache, curves, track, smooth

GATHER_KEYS = [(0, 0, 0), (.14, .035, .45), (.38, .30, 1.45),
               (.68, .78, 1.3), (.86, .97, .4), (1, 1, 0)]
PUSH_KEYS = [(0, 0, 0), (.22, -.07, 0), (.65, .50, 2.3),
             (1, .94, .3), (1.7, 1, 0)]
RETURN_KEYS = [(0, 0, 0), (.2, .10, .85), (.55, .65, 1.55),
               (.85, .96, .55), (1, 1, 0)]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def clamp(v, lo, hi):
    return min(hi, max(lo, v))


def hermite(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if t < b[0]:
            span = b[0]-a[0]
            u = (t-a[0])/span
            return ((2*u**3-3*u*u+1)*a[1]+(u**3-2*u*u+u)*span*a[2]
                    +(-2*u**3+3*u*u)*b[1]+(u**3-u*u)*span*b[2])
    return keys[-1][1]


def arc(a, b, c, d, t):
    v = 1-t
    return a*v**3+b*(3*v*v*t)+c*(3*v*t*t)+d*t**3


def warp(t, pairs):
    for a, b in zip(pairs, pairs[1:]):
        if t <= b[0]:
            return a[1]+(b[1]-a[1])*clamp((t-a[0])/(b[0]-a[0]), 0, 1)
    return pairs[-1][1]


def quaternion_angle(q):
    return math.degrees(2*math.acos(clamp(abs(q.normalized().w), 0, 1)))


def limit(q, degrees):
    q = q.normalized()
    if q.w < 0:
        q.negate()
    a = quaternion_angle(q)
    return Quaternion().slerp(q, min(1., degrees/max(a, 1e-8)))


def palm_frame(along, normal):
    along = along.normalized()
    normal = (normal-along*normal.dot(along)).normalized()
    return Matrix((along, normal.cross(along), normal)).transposed().to_quaternion()


def read_donor(name):
    raw = json.loads((DONOR/(name+'.json')).read_text(encoding='utf-8'))
    frames = []
    for row in raw['frames']:
        pose = {}
        for bone, values in row['component'].items():
            x, y, z, w = values['rotation_xyzw']
            q = Quaternion((w, x, y, z))
            pose[bone] = (
                DONOR_TO_M07@Vector(values['translation_cm']),
                (DONOR_TO_M07@q.to_matrix()@DONOR_TO_M07.transposed()).to_quaternion())
        frames.append(pose)
    return {'frames': frames, 'fps': raw['sample_hz'], 'seconds': raw['seconds'],
            'asset': raw['asset']}


def sample_donor(source, seconds):
    f = clamp(seconds*source['fps'], 0, len(source['frames'])-1)
    i = int(f)
    j = min(i+1, len(source['frames'])-1)
    alpha = f-i
    return {n: (pa.lerp(source['frames'][j][n][0], alpha),
                qa.slerp(source['frames'][j][n][1], alpha))
            for n, (pa, qa) in source['frames'][i].items()}


def sweep_parameters(t, contact, duration, side, donor):
    # The front-crossing portion of the same donor used by HES RampageV8.
    # It is warped into the preserved M07 contact contract, rather than moving
    # damage independently from the shoulder/elbow/wrist sweep.
    time_map = [(0, 0), (contact-.28, .23), (contact-.07, .30),
                (contact, .34), (contact+.16, .39), (duration, 1.)]
    s = sample_donor(donor, warp(t, time_map))
    neutral = donor['frames'][0]
    shoulder, elbow, wrist = [s[b][0] for b in ('upperarm_r', 'lowerarm_r', 'hand_r')]
    u = (elbow-shoulder).normalized()
    l = (wrist-elbow).normalized()
    # Donor windup goes behind and above its head, which reaches the M07 gill
    # roots. Retain its timing/arc but project that portion into an outward
    # chest-level anticipation. Its front crossing remains a horizontal sweep.
    azimuth = math.degrees(math.atan2((wrist-shoulder).x, -(wrist-shoulder).y))
    angle = clamp((azimuth+19.3)*.49, -72, 44)
    if side == 'l':
        angle *= -1
    active = smooth(t/.20)*(1-smooth((t-(duration-.30))/.30))
    elevation = clamp(-u.z, .32, .64)
    radial = math.sqrt(max(0., 1-elevation*elevation))
    sweep_dir = Vector((math.sin(math.radians(angle))*radial,
                        -math.cos(math.radians(angle))*radial, -elevation))
    sign = 1 if side == 'l' else -1
    entry = Vector((sign*.13, -.12, -.98)).normalized()
    upper = entry.lerp(sweep_dir, active).normalized()
    bend = 24+(clamp(math.degrees(u.angle(l)), 24, 88)-24)*active
    body_delta = s['spine_03'][1]@neutral['spine_03'][1].inverted()
    forward = body_delta@FWD
    yaw = math.degrees(math.atan2(forward.x, -forward.y))*.18
    yaw = clamp(yaw, -21, 21)*active*(1 if side == 'r' else -1)
    lean = clamp(math.degrees(math.asin(clamp(forward.z, -1, 1)))*.10, -2, 5)*active
    return {'side': side, 'upper_direction': upper, 'bend': bend,
            'body_yaw': yaw, 'body_lean': lean, 'finger_mode': 'claw',
            'finger_amount': .45+.43*active, 'wrist_flex': 2+5*active,
            'upper_roll': 0, 'forearm_roll': 0, 'active': active,
            'donor_seconds': warp(t, time_map), 'donor_angle_deg': azimuth}


def casting_parameters(t, role, rest, config):
    side = 'l'
    s = rest['upperarm_l'].translation
    e = rest['lowerarm_l'].translation
    w = rest['hand_l'].translation
    length = (e-s).length+(w-e).length
    player_shoulder = Vector(config['shoulder'])
    gather_delta = CAM_TO_M07@(Vector(config['gather_wrist'])-player_shoulder)
    scale = length*.68/gather_delta.length
    gather_delta *= scale
    release_delta = CAM_TO_M07@(Vector(config['release_wrist'])-player_shoulder)*scale
    entry = w-s
    gather_depart = CAM_TO_M07@Vector(config['gather_depart'])*scale*.40
    approach = CAM_TO_M07@Vector(config['gather_approach'])*scale*.55
    if role == 'MagicGather':
        phase = clamp(t/.95, 0, 1)
        amount = hermite(GATHER_KEYS, phase)
        goal = arc(entry, entry+gather_depart, gather_delta+approach, gather_delta, amount)
        palm = smooth((phase-.10)/.80)
        lean, yaw = 2*amount, -3*amount
        digits = smooth((phase-.04)/.72)
        stage = 'gather' if t < .95 else 'hold'
    else:
        if t < .12:
            amount = -smooth(t/.12)*.035
            palm, digits, stage = 0., 1., 'anticipation'
        elif t < .36:
            amount = hermite(PUSH_KEYS, (t-.12)/.18)
            palm, digits, stage = smooth((t-.14)/.16), 1., 'push'
        elif t < .44:
            amount, palm, digits, stage = 1., 1., 1., 'contact_hold'
        else:
            ret = hermite(RETURN_KEYS, clamp((t-.44)/.36, 0, 1))
            amount, palm, digits, stage = 1., 1-ret, 1-ret, 'recovery'
        goal = gather_delta.lerp(release_delta, amount)
        if .30 < t < .44:
            recoil = math.sin(2*math.pi*10*(t-.30))*(1-smooth((t-.30)/.14))
            goal += Vector((.25*recoil, 1.6*recoil, .4*recoil))
        if t >= .44:
            goal = arc(release_delta, release_delta+Vector((0, 8, -5)),
                       entry+Vector((0, -6, 5)), entry, ret)
        lean = track(t, [(0, 2), (.12, 1.5), (.30, 5), (.44, 5), (.80, 0)])
        yaw = track(t, [(0, -3), (.12, -5), (.30, 3), (.44, 3), (.80, 0)])
    return {'side': side, 'wrist_relative': goal, 'body_yaw': yaw, 'body_lean': lean,
            'finger_mode': 'cast', 'finger_amount': digits, 'palm_amount': palm,
            'upper_roll': 0., 'forearm_roll': 0., 'stage': stage,
            'release_role': role == 'MagicRelease', 'release_fraction': palm,
            'arm_blend': smooth(t/.22) if role == 'MagicGather' else 1-smooth((t-.52)/.28)}


def ik_directions(relative, upper_length, lower_length, torso, sign):
    target = torso@relative
    reach = clamp(target.length, abs(upper_length-lower_length)+3.,
                  (upper_length+lower_length)*.92)
    axis = target.normalized()
    # Elbow remains below and gently outside the shoulder/wrist line. The
    # nonstraight arm cannot switch elbow-plane sign during the palm push.
    pole = torso@Vector((sign*.22, 0, -1))
    pole = (pole-axis*pole.dot(axis)).normalized()
    along = (upper_length**2+reach**2-lower_length**2)/(2*reach)
    height = math.sqrt(max(0., upper_length**2-along**2))
    elbow = axis*along+pole*height
    wrist = axis*reach
    return elbow.normalized(), (wrist-elbow).normalized()


def bounded_palm(lower_delta, lower_direction, rest, torso, parameters):
    side = parameters['side']
    hand = 'hand_'+side
    source_along = (rest['middle_01_'+side].translation-rest[hand].translation).normalized()
    source_across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
    source_normal = source_along.cross(source_across).normalized()
    source_frame = palm_frame(source_along, source_normal)
    # Current player identity: gather palm up; release palm toward the target,
    # fingers rise. Palm-up and upright are distributed over a supported arm,
    # with third-person wrist limits, rather than copying FP shoulder offsets.
    p = parameters['palm_amount']
    gather_along, gather_normal = torso@Vector((.06, -.97, .24)), torso@UP
    release_along, release_normal = torso@Vector((.03, -.40, .917)), torso@FWD
    gather = palm_frame(gather_along, gather_normal)@source_frame.inverted()@rest[hand].to_quaternion()
    release = palm_frame(release_along, release_normal)@source_frame.inverted()@rest[hand].to_quaternion()
    if parameters['release_role']:
        goal = gather.slerp(release, p)
    else:
        goal = (lower_delta@rest[hand].to_quaternion()).slerp(gather, p)
    base = lower_delta@rest[hand].to_quaternion()
    goal = base.slerp(goal, parameters['arm_blend'])
    residual = goal@base.inverted()
    if residual.w < 0:
        residual.negate()
    axis = lower_direction.normalized()
    twist_angle = 2*math.atan2(Vector((residual.x, residual.y, residual.z)).dot(axis), residual.w)
    fore_roll = clamp(twist_angle*.65, math.radians(-24), math.radians(24))
    lower_delta = Quaternion(axis, fore_roll)@lower_delta
    base = lower_delta@rest[hand].to_quaternion()
    residual = goal@base.inverted()
    if residual.w < 0:
        residual.negate()
    full_twist_angle = 2*math.atan2(Vector((residual.x, residual.y, residual.z)).dot(axis), residual.w)
    full_twist = Quaternion(axis, full_twist_angle)
    swing = residual@full_twist.inverted()
    bounded_twist = Quaternion(axis, clamp(full_twist_angle, math.radians(-12), math.radians(12)))
    wrist = limit(swing, 35)@bounded_twist
    return lower_delta, wrist@base, math.degrees(fore_roll), quaternion_angle(wrist)


def build_action(rig, rest, ordered, idle_cache, role, frames, contact, donor, config):
    action = bpy.data.actions.new('A_M07_'+role+'_CombatMagicV14')
    action.use_fake_user = True
    motion.activate(rig, action)
    for p in rig.pose.bones:
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = Matrix.Identity(4)
        for channel in ('location', 'rotation_quaternion', 'scale'):
            p.keyframe_insert(data_path=channel, frame=0)
    duration = (frames-1)/FPS
    previous = {}
    authored = []
    for i in range(frames):
        frame, t = i+1, i/FPS
        bpy.context.scene.frame_set(frame)
        is_sweep = role.startswith('Sweep')
        parameters = (sweep_parameters(t, contact, duration, 'l' if role == 'SweepLeft' else 'r', donor)
                      if is_sweep else casting_parameters(t, role, rest, config))
        attacking = parameters['side']
        local = {n:m.copy() for n,m in idle_cache[i].items()}
        for name in local:
            if name.startswith(('clavicle_', 'upperarm_', 'lowerarm_', 'hand_',
                                'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                local[name] = Matrix.Identity(4)
        target, desired_fore, hand_goal, arm_deltas = {}, {}, {}, {}
        row = {'frame': frame, 'seconds': t, 'body_yaw_deg': parameters['body_yaw'],
               'body_lean_deg': parameters['body_lean']}
        if is_sweep:
            row.update(donor_seconds=parameters['donor_seconds'], donor_angle_deg=parameters['donor_angle_deg'])
        else:
            row['cast_stage'] = parameters['stage']
        for p in ordered:
            name, parent = p.name, p.parent.name if p.parent else None
            target[name] = p.bone.convert_local_to_pose(local[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
            if name in ('spine_02', 'spine_03', 'spine_04', 'spine_05'):
                q = (Quaternion(UP, math.radians(parameters['body_yaw']*.25))
                     @Quaternion(RIGHT, math.radians(parameters['body_lean']*.25))@target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            torso = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted() if 'spine_05' in target else Quaternion()
            if name.startswith('upperarm_'):
                side = name[-1]
                sign = 1 if side == 'l' else -1
                original_u = (rest['lowerarm_'+side].translation-rest[name].translation).normalized()
                original_l = (rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
                if side == attacking and not is_sweep:
                    upper_len = (rest['lowerarm_'+side].translation-rest[name].translation).length
                    lower_len = (rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
                    u, l = ik_directions(parameters['wrist_relative'], upper_len, lower_len, torso, sign)
                    # Blend out of the fixed-length IK before recovery ends;
                    # its reach ceiling must not leave a permanently bent
                    # elbow when the wrist has returned to the hanging pose.
                    weight = parameters['arm_blend']
                    u = (torso@original_u).lerp(u, weight).normalized()
                    l = (torso@original_l).lerp(l, weight).normalized()
                    delta = (torso@original_u).rotation_difference(u)@torso
                    desired_fore[side] = l
                else:
                    local_u = parameters['upper_direction'] if side == attacking else Vector((sign*.20, -.23, -.954)).normalized()
                    u = torso@local_u
                    delta = original_u.rotation_difference(local_u)
                    delta = torso@delta
                    bend = parameters['bend'] if side == attacking else 25.
                    hinge = torso@Vector((-1, 0, 0))
                    hinge = (hinge-u*hinge.dot(u)).normalized()
                    desired_fore[side] = Quaternion(hinge, math.radians(bend))@(delta@original_l)
                arm_deltas[side] = delta
                target[name] = Matrix.LocRotScale(target[name].translation, delta@rest[name].to_quaternion(), Vector((1, 1, 1)))
            elif name.startswith('lowerarm_'):
                side = name[-1]
                original_l = (rest['hand_'+side].translation-rest[name].translation).normalized()
                udelta = arm_deltas[side]
                # Transport the complete forearm from its actual reference;
                # this solves the wrist direction without adding an axial flip.
                delta = (udelta@original_l).rotation_difference(desired_fore[side])@udelta
                if side == attacking and not is_sweep:
                    delta, hand_goal[side], roll, residual = bounded_palm(delta, desired_fore[side], rest, torso, parameters)
                    row['forearm_roll_deg'] = roll
                    row['wrist_residual_deg'] = residual
                target[name] = Matrix.LocRotScale(target[name].translation, delta@rest[name].to_quaternion(), Vector((1, 1, 1)))
            elif name.startswith('hand_'):
                side = name[-1]
                lower = 'lowerarm_'+side
                delta = target[lower].to_quaternion()@rest[lower].to_quaternion().inverted()
                if side in hand_goal:
                    q = hand_goal[side]
                else:
                    flex = parameters['wrist_flex'] if side == attacking and is_sweep else 2.
                    q = Quaternion(target[lower].to_quaternion()@RIGHT, math.radians(flex))@delta@rest[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in name:
                side = name[-1]
                hand = 'hand_'+side
                hand_delta = target[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
                along = (rest['middle_01_'+side].translation-rest[hand].translation).normalized()
                across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
                normal = hand_delta@along.cross(across).normalized()
                direction = target[name].to_3x3()@Vector((0, 1, 0))
                axis = direction.cross(normal).normalized()
                digit, segment = name.split('_')[0], int(name.split('_')[1])
                if side == attacking and parameters['finger_mode'] == 'cast':
                    digit_config = config['digits'][digit]
                    release = parameters['release_fraction'] if parameters['release_role'] else 0
                    degrees = (digit_config['gather_flex'][segment-1]*(1-release)
                               +digit_config['release_flex'][segment-1]*release)
                    degrees *= parameters['finger_amount']
                else:
                    amount = parameters['finger_amount'] if side == attacking else .40
                    degrees = (7, 12, 9)[segment-1]*amount
                q = Quaternion(axis, math.radians(degrees))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}), invert=True)
            p.rotation_mode = 'QUATERNION'
            q = p.rotation_quaternion.copy()
            if name in previous and q.dot(previous[name]) < 0:
                q.negate()
            p.rotation_quaternion = q
            previous[name] = q.copy()
            p.scale = Vector((1, 1, 1))
            if name != 'pelvis':
                p.location = Vector()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=frame)
        # Source-authoring coordinates are retained for later editing. They are
        # not rendered or called runtime/visual acceptance.
        for side in ('l', 'r'):
            row['arm_'+side] = {part: list(target[part+'_'+side].translation)
                               for part in ('upperarm', 'lowerarm', 'hand')}
        authored.append(row)
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    return action, authored


def export(rig, action, path, frames):
    motion.activate(rig, action)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
        armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0,
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    original = json.loads((ROOT/'RecoveryOriginalV13/motion_manifest_v13.json').read_text(encoding='utf-8'))
    idle = bpy.data.actions[original['clips']['Idle']['action']]
    cache = neutral_body_cache(rig, 51, idle)
    donor = read_donor('Attack_Biped_Melee_A')
    config = json.loads((PROJECT/'Content/ColdSteelData/Skills/fireball_hand_pose.json').read_text(encoding='utf-8'))
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    rig.data.pose_position = 'POSE'
    entries, samples, actions = {}, {}, {}
    roles = [('SweepLeft', 46, .68), ('SweepRight', 51, .78),
             ('MagicGather', 34, None), ('MagicRelease', 25, .30)]
    for role, frames, contact in roles:
        action, authored = build_action(rig, rest, ordered, cache, role, frames, contact, donor, config)
        file = OUT/('A_M07_'+role+'.fbx')
        export(rig, action, file, frames)
        entry = {'file': str(file), 'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsCombatMagicV14/A_M07_'+role,
                 'action': action.name, 'frames': frames, 'fps': FPS, 'duration': (frames-1)/FPS,
                 'seconds': (frames-1)/FPS, 'reference_only_blender_frame': 0,
                 'exported_blender_frame_start': 1, 'exported_blender_frame_end': frames,
                 'loop': False, 'root_motion': False, 'contact_seconds': contact,
                 'impact_seconds': contact, 'impact_frame_zero_based': None if contact is None else contact*FPS,
                 'contact_window_seconds': .16 if role.startswith('Sweep') else None,
                 'contact_window_start_seconds': contact-.08 if role.startswith('Sweep') else None,
                 'contact_window_end_seconds': contact+.08 if role.startswith('Sweep') else None,
                 'hold_last_pose': role == 'MagicGather', 'bone_tracks': [b.name for b in rig.data.bones]}
        entries[role], samples[role], actions[role] = entry, authored, action
        print('M07_V14_MOTION_EXPORTED '+role+' '+str(file), flush=True)
    motion.activate(rig, actions['MagicGather'])
    scene.frame_start, scene.frame_end = 1, entries['MagicGather']['frames']
    scene.frame_set(0)
    source = OUT/'M07_Original_SweepCasting_V14.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    write(OUT/'motion_manifest_v14.json', {
        'revision': 'CombatMagicV14', 'fps': FPS, 'source': str(source), 'source_master': str(MASTER),
        'clips': entries, 'ue_skeleton': original.get('ue_skeleton', '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11'),
        'reference_bones': {n: motion.rows(m) for n, m in rest.items()},
        'bone_names': [b.name for b in rig.data.bones],
        'bone_parents': {b.name: b.parent.name if b.parent else None for b in rig.data.bones},
        'mesh_geometry_uv_skin_and_reference_preserved': True,
        'child_location_policy': 'Zero on every bone except original idle pelvis; unit scale; frame0 reference excluded',
        'sweep_reference': {'monster': 'HundredEyedSlag', 'current_role': 'AttackSweep_R',
            'current_asset': '/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R',
            'author': str(PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageV8/author_rampage.py'),
            'donor_asset': donor['asset'], 'donor_source': str(DONOR/'Attack_Biped_Melee_A.json'),
            'method': 'Actual donor shoulder/elbow/wrist arc, elbow bend and torso movement; front-facing chest-level projection, fixed M07 lengths, 21deg torso yaw cap, minimum shoulder swing, no axial shoulder roll; mirrored left',
            'donor_geometry_skin_or_nonhuman_bones_copied': False},
        'casting_reference': {'runtime': ['Source/FPSGAME/Skills/FPSFireballComponent.cpp',
            'Source/FPSGAME/Skills/FPSCastingMeshComponent.cpp', 'Source/FPSGAME/Skills/FireballCastMotion.h'],
            'pose_config': 'Content/ColdSteelData/Skills/fireball_hand_pose.json', 'pose_config_version': config['version'],
            'player_curve_contract': {'GatherKeys': GATHER_KEYS, 'PushKeys': PUSH_KEYS, 'ReturnKeys': RETURN_KEYS},
            'identity': 'Left hand slowly gathers palm-up, then supported arm pushes with palm toward target and raised fingers; small contact recoil and continuous recovery',
            'third_person_adaptation': 'Fixed shoulders and original lengths; two-bone reach limit .92; <=24deg forearm roll, <=35deg wrist swing and <=12deg wrist twist; no FP shoulder translation',
            'shared_elements': ['Fireball', 'IcePillar', 'Lightning']},
        'authoring_samples': samples, 'runtime_tested': False, 'rendered': False, 'ue_imported': False})
    print('M07_V14_SOURCES_SAVED '+str(source), flush=True)


if __name__ == '__main__':
    main()
