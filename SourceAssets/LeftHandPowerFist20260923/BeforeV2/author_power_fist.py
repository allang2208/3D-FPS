"""Author an independent left-arm gesture from the accepted V21 fist.

Blender background production only: editable source and four animation FBXs.
No renders, gameplay tests, or changes to the reference files.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector, Quaternion

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
CFG = json.loads((P / 'motion_config.json').read_text(encoding='utf-8'))
DONOR = ROOT / 'SourceAssets/RuneSword20260913/FistBraceGuardV21/AzureRunesword_Manny_Editable.blend'
BASE = ROOT / 'SourceAssets/GASPTraversal20260910/Native/TraversalArms_Editable.blend'
EXPORT = P / 'Export'
EXPORT.mkdir(exist_ok=True)
(P / 'References').mkdir(exist_ok=True)
FPS = CFG['fps']
ONE = Vector((1, 1, 1))
C = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, 1)))
bpy.context.preferences.filepaths.save_version = 0


def ease(t):
    t = max(0.0, min(1.0, t))
    return t*t*t*(t*(t*6.0-15.0)+10.0)


def pos(key):
    return C @ Vector(CFG[key]) * 0.01


def arc(a, b, c, d, t):
    v = 1.0-t
    return a*v**3+b*(3*v*v*t)+c*(3*v*t*t)+d*t**3


def frame(forward, normal):
    x = forward.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    return Matrix((x, x.cross(z), z)).transposed()


def anatomical(rest):
    origin = rest['hand_l'].translation
    f = (rest['middle_01_l'].translation-origin).normalized()
    side = rest['index_01_l'].translation-rest['pinky_01_l'].translation
    side = (side-f*side.dot(f)).normalized()
    return Matrix((side, f, side.cross(f))).transposed()


def finger(name):
    return name.endswith('_l') and name.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_'))


# Read the accepted source animation, not merely its asset name. The final
# guard sample has a free fist with the thumb outside the folded fingers.
bpy.ops.wm.open_mainfile(filepath=str(DONOR))
donor_rig = bpy.data.objects['SK_RuneSword_Rig']
donor_action = bpy.data.actions['A_RuneSword_Guard']
donor_rig.animation_data.action = donor_action
donor_rig.animation_data.action_slot = donor_action.slots[0]
donor_range = list(donor_action.frame_range)
donor_fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
bpy.context.scene.frame_set(round(donor_range[1]))
bpy.context.view_layer.update()
sr = {b.name: b.matrix_local.copy() for b in donor_rig.data.bones}
sp = {b.name: b.matrix.copy() for b in donor_rig.pose.bones}
source_info = {
    'blend': str(DONOR), 'action': donor_action.name,
    'frames': donor_range, 'fps': donor_fps,
    'duration': (donor_range[1]-donor_range[0])/donor_fps,
    'sample_frame': donor_range[1], 'loop': False,
    'reuse': 'Final closed left-fist rotations only; no sword or right-hand motion',
}
(P / 'References/guard_fist_source.json').write_text(json.dumps({
    **source_info,
    'bones': {n: {'rest': [list(v) for v in sr[n]], 'pose': [list(v) for v in sp[n]]}
              for n in sr if finger(n) or n == 'hand_l'},
}, indent=2), encoding='utf-8')

bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions['M4_idle']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
entry = {b.name: b.matrix.copy() for b in rig.pose.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
local = {n: rest[parents[n]].inverted()@m if parents[n] else m for n, m in rest.items()}
entry_local = {n: entry[parents[n]].inverted()@m if parents[n] else m for n, m in entry.items()}


def is_left(n):
    if not n.endswith('_l'):
        return False
    while n:
        if n == 'clavicle_l':
            return True
        n = parents[n]
    return False


left = [n for n in rest if is_left(n)]
digits = [n for n in rest if finger(n)]
# Conjugate rotations through source/target rest anatomy. Keep target bone
# translations and scale; no finger-length fitting or copying sword skeleton.
mapping = anatomical(rest) @ anatomical(sr).inverted()
source_hand_delta = sp['hand_l'].to_quaternion().to_matrix() @ sr['hand_l'].to_quaternion().to_matrix().transposed()
desired = {'hand_l': rest['hand_l'].to_3x3()}
closed = {}
for n in digits:
    delta = source_hand_delta.transposed() @ sp[n].to_quaternion().to_matrix() @ sr[n].to_quaternion().to_matrix().transposed()
    desired[n] = mapping @ delta @ mapping.inverted() @ rest[n].to_3x3()
    closed[n] = (desired[parents[n]].inverted() @ desired[n]).to_quaternion()

for obj in list(bpy.data.objects):
    if obj not in (rig, arms):
        bpy.data.objects.remove(obj, do_unlink=True)
rig.animation_data_clear()
for bone in rig.pose.bones:
    for constraint in list(bone.constraints):
        bone.constraints.remove(constraint)
    bone.rotation_mode = 'QUATERNION'
    bone.matrix_basis = Matrix.Identity(4)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

ru = rest['lowerarm_l'].translation-rest['upperarm_l'].translation
rl = rest['hand_l'].translation-rest['lowerarm_l'].translation
l1, l2 = ru.length, rl.length
origin = rest['hand_l'].translation
ref_normal = (rest['pinky_01_l'].translation-origin).cross(rest['index_01_l'].translation-origin).normalized()
ref_palm = frame(rest['middle_01_l'].translation-origin, ref_normal)
target_palm = frame(C@Vector(CFG['palm_forward']), C@Vector(CFG['palm_normal']))
target_hand = (target_palm @ ref_palm.inverted() @ rest['hand_l'].to_3x3()).to_quaternion()
ew, ea, ep = (entry[n].translation for n in ('hand_l', 'upperarm_l', 'lowerarm_l'))
eq = entry['hand_l'].to_quaternion()
end_w, end_a, end_p = pos('wrist'), pos('shoulder'), pos('elbow_pole')


def segment_frame(direction, across):
    x = direction.normalized()
    y = (across-x*across.dot(x)).normalized()
    return Matrix((x, y, x.cross(y))).transposed().to_quaternion()


def channels(t):
    start, contact = CFG['lift_start'], CFG['clench_end']
    recovery = CFG['recover_start']
    if t < start:
        u = ease(t/start)
        return ew+pos('anticipation_offset')*u, ea, ep, eq, 0.0, ease(t/.025)
    if t < contact:
        # Continuous fast acceleration, then short hard deceleration at closure.
        u = ease((t-start)/(contact-start))
        begin = ew+pos('anticipation_offset')
        w = arc(begin, begin+pos('lift_depart'), end_w+pos('lift_approach'), end_w, u)
        return w, ea.lerp(end_a, u), ep.lerp(end_p, u), eq.slerp(target_hand, u), 0.0, 1.0
    if t < recovery:
        # One small whole-arm braking impulse, not a wrist twist or looping shake.
        u = (t-contact)/(CFG['settle_end']-contact)
        brake = pos('brake_offset')*math.sin(math.pi*u)**2 if 0.0 < u < 1.0 else Vector()
        return end_w+brake, end_a+brake, end_p+brake, target_hand, 0.0, 1.0
    v = (t-recovery)/(CFG['duration']-recovery)
    u = ease(v)
    w = arc(end_w, end_w+pos('recovery_depart'), ew+pos('recovery_approach'), ew, u)
    return w, end_a.lerp(ea, u), end_p.lerp(ep, u), target_hand.slerp(eq, ease(v/.88)), v, 1.0-ease((v-.6)/.4)


def finger_weight(name, t):
    digit = name.split('_')[0]
    delay = CFG['finger_close_delay'][digit]
    close = ease((t-CFG['clench_start']-delay)/(CFG['clench_end']-CFG['clench_start']-delay))
    # Give the descending arm time to leave its forceful pose before opening.
    recover = (t-CFG['recover_start'])/(CFG['duration']-CFG['recover_start'])
    release_delay = 0.02 if digit == 'thumb' else .13
    return close*(1.0-ease((recover-release_delay)/.65))


def solve(t):
    if t <= 0.0 or t >= CFG['duration']:
        return {n: m.copy() for n, m in entry.items()}
    w, a, pole, hq, recover, weight = channels(t)
    distance = w-a
    if distance.length > (l1+l2)*.93:
        a += distance.normalized()*(distance.length-(l1+l2)*.93)
    direction = (w-a).normalized()
    length = min((w-a).length, l1+l2-.00001)
    bend = pole-a
    bend = (bend-direction*bend.dot(direction)).normalized()
    along = (l1*l1-l2*l2+length*length)/(2.0*length)
    e = a+direction*along+bend*math.sqrt(max(0.0, l1*l1-along*along))
    ud, ld = (e-a).normalized(), (w-e).normalized()
    hand_deform = hq @ rest['hand_l'].to_quaternion().inverted()
    across = ref_palm.col[1]
    fd = segment_frame(ld, hand_deform@across) @ segment_frame(rl, across).inverted()
    fq = fd @ rest['lowerarm_l'].to_quaternion()
    # V21's accepted elbow fix: transport the forearm frame to the upper arm.
    # Skin helpers inherit complete segment transforms through rest-local data.
    upper_deform = (fd@ru.normalized()).rotation_difference(ud) @ fd
    uq = upper_deform @ rest['upperarm_l'].to_quaternion()
    arm_mix = ease((t-CFG['lift_start'])/(CFG['clench_end']-CFG['lift_start']))*(1-ease(recover))
    for name, axis, goal in (('upperarm_l', ud, uq), ('lowerarm_l', ld, fq)):
        source = entry[name].to_quaternion()
        rest_axis = ru if name == 'upperarm_l' else rl
        source_axis = (source@rest[name].to_quaternion().inverted())@rest_axis.normalized()
        aligned = source_axis.rotation_difference(axis)@source
        if name == 'upperarm_l':
            uq = aligned.slerp(goal, arm_mix)
        else:
            fq = aligned.slerp(goal, arm_mix)
    values = {n: m.copy() for n, m in entry.items()}
    upper_matrix = Matrix.LocRotScale(a, uq, ONE)
    support_delta = upper_matrix @ entry['upperarm_l'].inverted()
    for n in left:
        parent = parents[n]
        if n == 'clavicle_l':
            m = support_delta @ entry[n]
        elif n == 'upperarm_l':
            m = upper_matrix
        elif n == 'lowerarm_l':
            m = Matrix.LocRotScale(e, fq, ONE)
        elif n == 'hand_l':
            m = Matrix.LocRotScale(w, hq, ONE)
        elif n in closed:
            loc, q, scale = entry_local[n].decompose()
            if t < CFG['recover_start']:
                # Release the old grip before the snap. This exposes the
                # closing motion instead of lifting an already closed fist.
                relaxed = local[n].to_quaternion().slerp(q, .25)
                q = q.slerp(relaxed, ease(t/.105))
            q = q.slerp(closed[n], finger_weight(n, t))
            m = values[parent] @ Matrix.LocRotScale(loc, q, scale)
        else:
            m = values[parent] @ local[n]
        values[n] = m
    targets = {n: values[parents[n]].inverted()@values[n] for n in left}
    for n in left:
        target, base = targets[n], entry_local[n]
        m = Matrix.LocRotScale(base.translation.lerp(target.translation, weight),
                              base.to_quaternion().slerp(target.to_quaternion(), weight),
                              base.to_scale().lerp(target.to_scale(), weight))
        values[n] = values[parents[n]] @ m
    return values


scene.render.fps = FPS
scene.render.fps_base = 1.0
clips = [
    ('A_LeftHand_PowerFist', 1.0, lambda t: t, False),
    ('A_LeftHand_PowerFist_Raise', .30, lambda t: t, False),
    ('A_LeftHand_PowerFist_Hold', .50, lambda t: .40, True),
    ('A_LeftHand_PowerFist_Recover', .48, lambda t: CFG['recover_start']+t, False),
]
records = []
for name, duration, source_time, loop in clips:
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    last = round(duration*FPS)
    scene.frame_start, scene.frame_end = 0, last
    previous = {}
    for f in range(last+1):
        values = solve(source_time(f/FPS))
        for n in rest:
            if n not in left and f not in (0, last):
                continue
            parent = parents[n]
            m = values[parent].inverted()@values[n] if parent else values[n]
            loc, q, scale = (local[n].inverted()@m).decompose()
            if n in previous and q.dot(previous[n]) < 0:
                q.negate()
            previous[n] = q.copy()
            bone = rig.pose.bones[n]
            bone.location, bone.rotation_quaternion, bone.scale = loc, q, scale
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=f, group=n)
    rig.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    scene.frame_set(0)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')), use_selection=True,
                            object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                            add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                            bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0,
                            bake_anim_force_startend_keying=True)
    records.append({'name': name, 'fps': FPS, 'frames': [0, last],
                    'duration': duration, 'loop': loop, 'fbx': str(EXPORT/(name+'.fbx'))})
    print('POWER_FIST_EXPORTED', name, flush=True)

rig.animation_data.action = bpy.data.actions['A_LeftHand_PowerFist']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, FPS
scene.frame_set(round(CFG['clench_end']*FPS))
for frame_index, label in [(0, 'Start'), (round(CFG['clench_start']*FPS), 'CloseStart'),
                           (round(CFG['clench_end']*FPS), 'FistLocked'),
                           (round(CFG['settle_end']*FPS), 'Settled'),
                           (round(CFG['recover_start']*FPS), 'Recover'), (FPS, 'End')]:
    scene.timeline_markers.new(label, frame=frame_index)
cam_data = bpy.data.cameras.new('Source_FirstPerson')
camera = bpy.data.objects.new('Source_FirstPerson', cam_data)
scene.collection.objects.link(camera)
camera.location = (0, 0, 0)
camera.rotation_euler = (math.pi/2, 0, 0)
cam_data.lens = 18
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'LeftHand_PowerFist_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({
    'revision': CFG['revision'], 'source_fist': source_info, 'base_rig': str(BASE),
    'mesh': arms.name, 'skeleton_route': 'Current M4 Manny viewmodel skeleton',
    'clips': records, 'fist_locked_seconds': CFG['clench_end'],
    'runtime_integration': 'Independent assets only; future use must layer clavicle_l descendants',
    'right_arm_and_weapon': 'Held unchanged at source M4_idle frame 0',
    'tests_or_renders_run': False,
}, indent=2), encoding='utf-8')
print('POWER_FIST_SOURCE_SAVED', flush=True)
