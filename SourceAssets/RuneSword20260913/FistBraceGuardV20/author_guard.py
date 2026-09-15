"""Photo-directed single-right-hand sword guard with a left-fist blade brace.

New guard poses are solved from rest anatomy. V19 supplies the retained rig and
ready endpoints only. This script authors assets; it does not render or test.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
CFG = json.loads((P / 'pose_config.json').read_text(encoding='utf-8'))
SOURCE = P.parent / 'GuardPoseV19/AzureRunesword_Manny_Editable.blend'
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
FPS = CFG['fps']
RAISE = CFG['raise_seconds']
BREAK = CFG['break_seconds']
ONE = Vector((1, 1, 1))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.context.scene
r = bpy.data.objects['SK_RuneSword_Rig']
ready_action = bpy.data.actions['A_RuneSword_Slash1']
r.animation_data.action = ready_action
r.animation_data.action_slot = ready_action.slots[0]
s.frame_set(0)
bpy.context.view_layer.update()
BASE = {b.name: b.matrix.copy() for b in r.pose.bones}
REST = {b.name: b.matrix_local.copy() for b in r.data.bones}
PARENT = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
LOCAL = {n: REST[PARENT[n]].inverted() @ m if PARENT[n] else m for n, m in REST.items()}
ENTRY_LOCAL = {n: BASE[PARENT[n]].inverted() @ m if PARENT[n] else m for n, m in BASE.items()}
SWORD = BASE['WPN_root']
RIGHT_GRIP = SWORD.inverted() @ BASE['hand_r']
FINGER_NAMES = [n for n in REST if n.endswith('_l') and n.startswith(('index', 'middle', 'ring', 'pinky', 'thumb'))]


def ease(t):
    t = max(0., min(1., t))
    return t*t*t*(t*(t*6.-15.)+10.)


def blend(a, b, t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, t),
                              a.to_quaternion().slerp(b.to_quaternion(), t), ONE)


def arc(a, b, c, d, t):
    v = 1.-t
    return a*(v*v*v)+b*(3*v*v*t)+c*(3*v*t*t)+d*(t*t*t)


def frame(forward, normal):
    x = forward.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    return Matrix((x, x.cross(z), z)).transposed()


WRIST0 = REST['hand_l'].translation
REF_NORMAL = (REST['pinky_01_l'].translation-WRIST0).cross(REST['index_01_l'].translation-WRIST0).normalized()
REF_PALM = frame(REST['middle_01_l'].translation-WRIST0, REF_NORMAL)
PALM = frame(Vector(CFG['palm_forward']), Vector(CFG['palm_normal']))
HAND_ROT = (PALM @ REF_PALM.inverted() @ REST['hand_l'].to_3x3()).to_quaternion()


def finger_profile(profile):
    """Build a grouped fist without shifting knuckles or changing bone lengths.

    Carry the curl-plane normal through the full rotation, including beyond 90
    degrees. Projecting a fixed palm normal there would flip the finger roll.
    """
    pose = {n: m.copy() for n, m in REST.items()}
    for n in FINGER_NAMES:
        parent = PARENT[n]
        m = pose[parent] @ LOCAL[n]
        parts = n.split('_')
        if len(parts) == 3 and parts[1].isdigit():
            digit = profile[parts[0]]
            k = int(parts[1])-1
            next_name = f'{parts[0]}_{k+2:02d}_l'
            if next_name in REST:
                rd = REST[next_name].translation-REST[n].translation
            else:
                rd = REST[n].to_quaternion() @ (REST[parent].to_quaternion().inverted() @ (REST[n].translation-REST[parent].translation))
            spread = digit['spread'][k] if isinstance(digit['spread'], list) else digit['spread']
            angle = math.radians(spread)
            planar = REF_PALM @ Vector((math.cos(angle), math.sin(angle), 0))
            neutral = frame(planar, REF_NORMAL)
            curl = Quaternion(neutral.col[1], math.radians(digit['flex'][k]))
            target = curl.to_matrix() @ neutral
            q = (target @ frame(rd, REF_NORMAL).inverted() @ REST[n].to_3x3()).to_quaternion()
            m = Matrix.LocRotScale(m.translation, q, ONE)
        pose[n] = m
    return {n: pose[PARENT[n]].inverted() @ pose[n] for n in FINGER_NAMES}


FIST = finger_profile(CFG['fist'])
OPEN = finger_profile(CFG['release'])

# Use the actual retained blade face and dorsal glove pad as authoring anchors.
# Source mesh coordinates remain untouched; this fits the complete left hand.
blade = bpy.data.objects['RuneSword_Blade']
blade_points = [REST['WPN_root'].inverted() @ v.co for v in blade.data.vertices]
contact_height = CFG['blade_contact_height_m']
face_points = [v for v in blade_points if abs(v.z-contact_height) < .012 and abs(v.x) < .018]
face_y = min(v.y for v in face_points)
CONTACT_LOCAL = Vector((0., face_y, contact_height))
arms = bpy.data.objects['SK_Manny_Arms_Export']
skin_to_rig = r.matrix_world.inverted() @ arms.matrix_world
pad_samples = []
for v in arms.data.vertices:
    p = REF_PALM.inverted() @ (skin_to_rig @ v.co-WRIST0)
    if .055 < p.x < .09 and abs(p.y) < .021 and -.06 < p.z < 0.:
        pad_samples.append(p.z)
pad_samples.sort()
pad_depth = pad_samples[round((len(pad_samples)-1)*.08)]
PAD_LOCAL = Vector((CFG['dorsal_pad_forward_m'], 0., pad_depth))
direction = Vector(CFG['blade_direction']).normalized()
normal = -PALM.col[2]
normal = (normal-direction*normal.dot(direction)).normalized()
GUARD_SWORD = Matrix((normal.cross(direction), normal, direction)).transposed().to_4x4()
GUARD_SWORD.translation = Vector(CFG['hilt_m'])
# The palm faces the player and the glove's back presses the near broad face.
GUARD_HAND = Matrix.LocRotScale(GUARD_SWORD @ CONTACT_LOCAL-PALM @ PAD_LOCAL, HAND_ROT, ONE)
LEFT_CONTACT = GUARD_SWORD.inverted() @ GUARD_HAND


def solve_arm(pose, side, hand, weight):
    """Finite two-bone solution; supported elbows, full rest-segment helpers."""
    upper, fore, wrist = [part+'_'+side for part in ('upperarm', 'lowerarm', 'hand')]
    old_a = REST[upper].translation
    old_e = REST[fore].translation
    old_h = REST[wrist].translation
    ru = old_e-old_a
    rf = old_h-old_e
    l1, l2 = ru.length, rf.length
    label = 'left' if side == 'l' else 'right'
    a = BASE[upper].translation.lerp(Vector(CFG['shoulder_'+label+'_m']), weight)
    h = hand.translation
    reach = h-a
    if reach.length > (l1+l2)*.95:
        a += reach.normalized()*(reach.length-(l1+l2)*.95)
    reach = h-a
    distance = reach.length
    axis = reach.normalized()
    hand_deform = hand.to_quaternion() @ REST[wrist].to_quaternion().inverted()
    neutral_fore = hand_deform @ rf.normalized()
    ideal_elbow = h-neutral_fore*l2
    # The photo determines the wrist and forearm. An anatomical elbow guide
    # stabilizes the bending plane without forcing both forearms to cross.
    guide = BASE[fore].translation.lerp(Vector(CFG['elbow_'+label+'_m']), weight)
    wanted = ideal_elbow.lerp(guide, .22)
    pole = wanted-a-axis*(wanted-a).dot(axis)
    pole.normalize()
    along = (l1*l1-l2*l2+distance*distance)/(2.*distance)
    e = a+axis*along+pole*math.sqrt(max(0., l1*l1-along*along))
    ud, fd = (e-a).normalized(), (h-e).normalized()
    uq = (frame(ud, ud.cross(fd)) @ frame(ru, ru.cross(rf)).inverted() @ REST[upper].to_3x3()).to_quaternion()
    fq = neutral_fore.rotation_difference(fd) @ hand_deform @ REST[fore].to_quaternion()
    # Blend the neutral rest-segment roll out of the retained endpoint only
    # around entry. The held guard never inherits V19 auxiliary-bone rotation.
    for name, point, direction_now, direction_base, goal in (
        (upper, a, ud, BASE[fore].translation-BASE[upper].translation, uq),
        (fore, e, fd, BASE[wrist].translation-BASE[fore].translation, fq)):
        transported = direction_base.normalized().rotation_difference(direction_now) @ BASE[name].to_quaternion()
        q = transported.slerp(goal, ease(weight/.32))
        pose[name] = Matrix.LocRotScale(point, q, ONE)
    pose['clavicle_'+side].translation += a-BASE[upper].translation
    pose[wrist] = hand
    for prefix, parent in (('upperarm', upper), ('lowerarm', fore)):
        for idx in ('01', '02'):
            name = f'{prefix}_twist_{idx}_{side}'
            if name in REST:
                rest_relative = REST[parent].inverted() @ REST[name]
                entry_relative = BASE[parent].inverted() @ BASE[name]
                pose[name] = pose[parent] @ blend(entry_relative, rest_relative, ease(weight/.32))


def finger_mix(first, second, w):
    return {n: blend(first[n], second[n], w) for n in FINGER_NAMES}


ENTRY_FINGERS = {n: ENTRY_LOCAL[n] for n in FINGER_NAMES}


def assemble(sword, hand, fingers, weight):
    pose = {n: m.copy() for n, m in BASE.items()}
    solve_arm(pose, 'r', sword @ RIGHT_GRIP, weight)
    solve_arm(pose, 'l', hand, weight)
    for n in FINGER_NAMES:
        pose[n] = pose[PARENT[n]] @ fingers[n]
    right_delta = pose['hand_r'] @ BASE['hand_r'].inverted()
    for n in BASE:
        if n.endswith('_r') and n.startswith(('index', 'middle', 'ring', 'pinky', 'thumb')):
            pose[n] = right_delta @ BASE[n]
    for n in ('WPN_root', 'Blade_Base', 'Blade_Tip'):
        pose[n] = sword @ SWORD.inverted() @ BASE[n]
    return pose


def raised(t):
    if t <= 0.:
        return {n: m.copy() for n, m in BASE.items()}
    u = max(0., min(1., t/RAISE))
    w = ease(u)
    sword = blend(SWORD, GUARD_SWORD, ease((u-.08)/.92))
    sword.translation += Vector((.014, -.012, .035))*math.sin(math.pi*u)**2
    hand = blend(BASE['hand_l'], GUARD_HAND, ease((u-.03)/.85))
    hand.translation = arc(BASE['hand_l'].translation,
                           BASE['hand_l'].translation+Vector((-.16, -.09, .055)),
                           GUARD_HAND.translation+Vector((-.12, -.07, -.025)),
                           GUARD_HAND.translation, w)
    fingers = finger_mix(ENTRY_FINGERS, OPEN, ease(u/.30))
    fingers = finger_mix(fingers, FIST, ease((u-.28)/.53))
    return assemble(sword, hand, fingers, w)


raise_frames = [raised(f/FPS) for f in range(round(RAISE*FPS)+1)]
guard = raise_frames[-1]
hit_frames = []
for f in range(CFG['hit_frames']+1):
    t = f/FPS
    duration = CFG['hit_frames']/FPS
    force = ease(t/.044) if t < .044 else 1.-ease((t-.044)/(duration-.044))
    recoil = (Matrix.Translation(GUARD_SWORD.translation+Vector((0., -.028, -.009))*force)
              @ Matrix.Rotation(math.radians(2.4)*force, 4, 'X')
              @ Matrix.Translation(-GUARD_SWORD.translation))
    sword = recoil @ GUARD_SWORD
    hit_frames.append(assemble(sword, sword @ LEFT_CONTACT, FIST, 1.))
hit_frames[0] = guard
hit_frames[-1] = guard

drop = GUARD_SWORD.copy()
drop.translation += Vector((.075, -.025, -.115))
drop = (Matrix.Translation(drop.translation) @ Matrix.Rotation(math.radians(-13), 4, 'Y')
        @ GUARD_SWORD.to_quaternion().to_matrix().to_4x4())
break_frames = []
for f in range(round(BREAK*FPS)+1):
    t = f/FPS
    if t <= .105:
        sword = blend(GUARD_SWORD, drop, ease(t/.105))
        hand = sword @ LEFT_CONTACT
        hand.translation += Vector((-.035, -.045, 0.))*ease((t-.035)/.07)
        fingers = finger_mix(FIST, OPEN, ease((t-.060)/.12))
        weight = 1.
    else:
        u = (t-.105)/(BREAK-.105)
        weight = 1.-ease(u)
        sword = blend(drop, SWORD, ease(u))
        start_hand = drop @ LEFT_CONTACT
        start_hand.translation += Vector((-.035, -.045, 0.))
        hand = blend(start_hand, BASE['hand_l'], ease(u))
        hand.translation = arc(start_hand.translation,
                               start_hand.translation+Vector((-.09, -.08, -.05)),
                               BASE['hand_l'].translation+Vector((-.09, -.035, .015)),
                               BASE['hand_l'].translation, ease(u))
        fingers = finger_mix(FIST, OPEN, ease((t-.060)/.12))
        fingers = finger_mix(fingers, ENTRY_FINGERS, ease((u-.56)/.44))
    break_frames.append(assemble(sword, hand, fingers, weight))
break_frames[0] = guard
break_frames[-1] = {n: m.copy() for n, m in BASE.items()}


def export(name, frames):
    full_name = 'A_RuneSword_'+name
    old = bpy.data.actions.get(full_name)
    if old:
        old.name = 'REF_V19_'+full_name
        old.use_fake_user = True
    action = bpy.data.actions.new(full_name)
    action.use_fake_user = True
    r.animation_data.action = action
    s.frame_start = 0
    s.frame_end = len(frames)-1
    previous = {}
    for f, pose in enumerate(frames):
        s.frame_set(f)
        for b in r.pose.bones:
            local = pose[PARENT[b.name]].inverted() @ pose[b.name] if PARENT[b.name] else pose[b.name]
            loc, q, scale = (LOCAL[b.name].inverted() @ local).decompose()
            if b.name in previous and q.dot(previous[b.name]) < 0.:
                q.negate()
            previous[b.name] = q.copy()
            b.rotation_mode = 'QUATERNION'
            b.location, b.rotation_quaternion, b.scale = loc, q, scale
            for channel in ('location', 'rotation_quaternion', 'scale'):
                b.keyframe_insert(channel, frame=f, group=b.name)
    r.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    r.hide_set(False)
    r.select_set(True)
    bpy.context.view_layer.objects.active = r
    bpy.ops.export_scene.fbx(filepath=str(OUT/(full_name+'.fbx')), use_selection=True,
        object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0)
    print('FIST_BRACE_V20_EXPORTED '+full_name, flush=True)
    return action


s.render.fps = FPS
s.render.fps_base = 1.
guard_action = export('Guard', raise_frames)
export('GuardHit', hit_frames)
export('GuardBreak', break_frames)
r.animation_data.action = guard_action
r.animation_data.action_slot = guard_action.slots[0]
s.frame_start = 0
s.frame_end = round(RAISE*FPS)
s.frame_set(s.frame_end)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
record = dict(CFG)
record.update({'source': str(SOURCE), 'ready_reference': 'A_RuneSword_Slash1 frame 0',
    'guard_wrist_m': list(GUARD_HAND.translation), 'dorsal_pad_m': list(PAD_LOCAL),
    'blade_contact_local_m': list(CONTACT_LOCAL),
    'guard_hit_seconds': CFG['hit_frames']/FPS,
    'reference_interpretation': 'Palm faces player, fingers closed and thumb outside; elbow and blade support reconstructed in 3D from a single photograph',
    'arms': 'Rest-based whole segments and auxiliary bones; independent shoulder/elbow support; no hilt revolution search',
    'scope': 'Guard, GuardHit, GuardBreak only; existing runtime asset names',
    'renders_or_tests_run': False, 'acceptance': 'Pending user playtest'})
(P/'authoring.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('RUNESWORD_V20_AUTHORED', flush=True)
