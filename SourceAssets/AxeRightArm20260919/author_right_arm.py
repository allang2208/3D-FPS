"""Re-author the axe's right shoulder/elbow support around confirmed impact.

Keeps WPN_root, both hands, fingers, left arm and the 200 ms hit pause.
Swing's approach and recovery share the corrected contact pose. Production only.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'SourceAssets/AxeHitPause20260919/Axe_HitPause_Editable.blend'
OUT = HERE / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
FPS = 300
PROFILE = json.loads((ROOT/'Content/ColdSteelData/axe_impact_motion.json').read_text(encoding='utf-8'))
STATIONS = json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text(encoding='utf-8'))['skin_stations']['r']
CONFIG = {'shoulder_support_m': [.005, .025, -.004], 'pole_limit_degrees': 60.,
          'upper_arm_roll_share': .20, 'upper_arm_roll_limit_degrees': 18.,
          'preferred_elbow_below_wrist_m': .07, 'approach_start_s': .34,
          'approach_complete_s': .46, 'recovery_blend_out_s': .76}

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
U, F, H = 'upperarm_r', 'lowerarm_r', 'hand_r'
upper_rest = (rest[F].translation - rest[U].translation).normalized()
fore_rest = (rest[H].translation - rest[F].translation).normalized()
rest_normal = upper_rest.cross(fore_rest).normalized()
L1 = (rest[F].translation-rest[U].translation).length
L2 = (rest[H].translation-rest[F].translation).length


def ease(t):
    t = max(0., min(1., t))
    return t*t*t*(10.-15.*t+6.*t*t)


def frame_rotation(axis, normal):
    return Matrix((axis, normal, axis.cross(normal))).transposed().to_quaternion()


REST_UP_FRAME = frame_rotation(upper_rest, rest_normal)
REST_FORE_FRAME = frame_rotation(fore_rest, rest_normal)


def axial_delta(a, b, axis):
    delta = a @ b.inverted()
    angle = 2*math.atan2(Vector((delta.x, delta.y, delta.z)).dot(axis), delta.w)
    return (angle+math.pi) % (2*math.pi)-math.pi


def aligned_source(source, name, old_axis, new_axis):
    return old_axis.rotation_difference(new_axis) @ source[name].to_quaternion()


def corrected(source, weight):
    if weight <= 1e-8:
        return {n: m.copy() for n, m in source.items()}
    pose = {n: m.copy() for n, m in source.items()}
    hand = source[H]
    target = hand.translation
    shoulder = source[U].translation + Vector(CONFIG['shoulder_support_m'])*weight
    reach = target - shoulder
    direction = reach.normalized()
    shoulder += direction*max(0., reach.length-.94*(L1+L2))
    distance = (target-shoulder).length
    along = (L1*L1-L2*L2+distance*distance)/(2*distance)
    radius = math.sqrt(max(0., L1*L1-along*along))
    center = shoulder+direction*along
    natural = Vector((.55, -.12, -1.))
    natural = (natural-direction*natural.dot(direction)).normalized()
    hand_deform = hand.to_quaternion() @ rest[H].to_quaternion().inverted()
    neutral_fore = hand_deform @ fore_rest

    def geometry(angle):
        elbow = center+(Quaternion(direction, angle) @ natural)*radius
        up_axis = (elbow-shoulder).normalized()
        fore_axis = (target-elbow).normalized()
        # The actual bend plane defines the humerus and elbow hinge. The old
        # solver could spend almost 95 degrees rolling the upper arm to chase
        # wrist orientation; this construction starts at the elbow itself.
        normal = up_axis.cross(fore_axis).normalized()
        up_deform = frame_rotation(up_axis, normal) @ REST_UP_FRAME.inverted()
        fore_hinge = frame_rotation(fore_axis, normal) @ REST_FORE_FRAME.inverted()
        full_fore = neutral_fore.rotation_difference(fore_axis) @ hand_deform
        roll = axial_delta(full_fore, fore_hinge, fore_axis)
        wrist_bend = neutral_fore.angle(fore_axis)
        raised_elbow = max(0., elbow.z-target.z+CONFIG['preferred_elbow_below_wrist_m'])
        # Bounded anatomical fitting, not a free fingertip/contact optimization.
        cost = 2.*wrist_bend*wrist_bend + .12*roll*roll + (raised_elbow*18.)**2 + .08*angle*angle
        return cost, elbow, up_axis, fore_axis, up_deform, full_fore

    cap = math.radians(CONFIG['pole_limit_degrees'])
    chosen = min((-cap+2*cap*i/60 for i in range(61)), key=lambda a: geometry(a)[0])
    lo, hi = max(-cap, chosen-cap/30), min(cap, chosen+cap/30)
    for _ in range(14):
        a, b = lo+(hi-lo)*.382, lo+(hi-lo)*.618
        if geometry(a)[0] < geometry(b)[0]:
            hi = b
        else:
            lo = a
    angle = (lo+hi)*.5
    # Blend poles on the shoulder/wrist circle, preserving both bone lengths.
    original_pole = source[F].translation-center
    original_pole -= direction*original_pole.dot(direction)
    original_pole.normalize()
    desired_pole = Quaternion(direction, angle) @ natural
    delta = math.atan2(direction.dot(original_pole.cross(desired_pole)), original_pole.dot(desired_pole))
    pole = Quaternion(direction, delta*weight) @ original_pole
    elbow = center+pole*radius
    up_axis = (elbow-shoulder).normalized()
    fore_axis = (target-elbow).normalized()
    normal = up_axis.cross(fore_axis).normalized()
    up_deform = frame_rotation(up_axis, normal) @ REST_UP_FRAME.inverted()
    fore_hinge = frame_rotation(fore_axis, normal) @ REST_FORE_FRAME.inverted()
    full_fore = neutral_fore.rotation_difference(fore_axis) @ hand_deform
    roll = axial_delta(full_fore, fore_hinge, fore_axis)
    limit = math.radians(CONFIG['upper_arm_roll_limit_degrees'])
    share = max(-limit, min(limit, roll*CONFIG['upper_arm_roll_share']))
    desired_upper = Quaternion(up_axis, share) @ up_deform @ rest[U].to_quaternion()
    source_up_axis = (source[F].translation-source[U].translation).normalized()
    source_fore_axis = (source[H].translation-source[F].translation).normalized()
    upper_q = aligned_source(source, U, source_up_axis, up_axis).slerp(desired_upper, weight)
    final_up_deform = upper_q @ rest[U].to_quaternion().inverted()
    no_roll = (final_up_deform @ fore_rest).rotation_difference(fore_axis) @ final_up_deform
    residual = axial_delta(full_fore, no_roll, fore_axis)
    pose['clavicle_r'].translation += shoulder-source[U].translation
    pose[U] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
    for index in ('01', '02'):
        helper = 'upperarm_twist_' + index + '_r'
        pose[helper] = pose[U] @ rest[U].inverted() @ rest[helper]
    # Start the forearm at the elbow's anatomical frame, then apply its residual
    # pronation progressively at this Manny mesh's recorded skin stations.
    # Do not apply partial rotations to an already fully rotated parent bone.
    full_fore_matrix = Matrix.LocRotScale(elbow, full_fore @ rest[F].to_quaternion(), Vector((1, 1, 1)))
    for name, station in STATIONS.items():
        position = (full_fore_matrix @ rest[F].inverted() @ rest[name]).translation
        desired = Quaternion(fore_axis, residual*station) @ no_roll @ rest[name].to_quaternion()
        original_q = aligned_source(source, name, source_fore_axis, fore_axis)
        pose[name] = Matrix.LocRotScale(position, original_q.slerp(desired, weight), Vector((1, 1, 1)))
    # Hand/finger world matrices in pose remain the exact source matrices. Their
    # local bases are reconstructed after the parents, so neither grip moves.
    return pose


samples = {}
for clip, duration in (('Swing', .68), ('HitRecover', .44)):
    name = 'A_Harvest_Axe_' + clip
    original = bpy.data.actions[name]
    rig.animation_data.action = original
    rig.animation_data.action_slot = original.slots[0]
    frames = []
    for frame in range(round(duration*FPS)+1):
        scene.frame_set(frame)
        frames.append({b.name: b.matrix.copy() for b in rig.pose.bones})
    samples[clip] = frames

report = {'revision': 'H4_V5_ThumbFix1_HitPause200ms_RightElbow1', 'source': str(SOURCE),
          'fps': FPS, 'config': CONFIG, 'skin_stations': STATIONS,
          'runtime_tested': False, 'rendered': False, 'clips': {}}
contact_pose = None
for clip, duration in (('Swing', .68), ('HitRecover', .44)):
    name = 'A_Harvest_Axe_' + clip
    original = bpy.data.actions[name]
    original.name = 'REF_BeforeRightElbow_' + name
    original.use_fake_user = True
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps = FPS
    scene.render.fps_base = 1
    scene.frame_start = 0
    scene.frame_end = round(duration*FPS)
    previous = {}
    for frame, source in enumerate(samples[clip]):
        scene.frame_set(frame)
        if clip == 'Swing':
            t = frame/FPS
            time = t*PROFILE['contact_seconds']/.24 if t <= .24 else \
                PROFILE['contact_seconds']+(t-.24)*(PROFILE['swing_seconds']-PROFILE['contact_seconds'])/.44
            weight = ease((time-CONFIG['approach_start_s'])/(CONFIG['approach_complete_s']-CONFIG['approach_start_s']))
            weight *= 1.-ease((time-.60)/.25)
            pose = corrected(source, weight)
            if frame == round(.24*FPS):
                contact_pose = {n: m.copy() for n, m in pose.items()}
        else:
            age = frame/scene.frame_end*PROFILE['hit_recover_seconds']
            weight = 1.-ease((age-CONFIG['recovery_blend_out_s'])/
                            (PROFILE['hit_recover_seconds']-CONFIG['recovery_blend_out_s']))
            pose = {n: m.copy() for n, m in contact_pose.items()} if age <= PROFILE['hit_stop_seconds'] else corrected(source, weight)
        for bone in rig.pose.bones:
            parent_inverse = pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted() @ parent_inverse @ pose[bone.name]
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name]) < 0:
                q.negate()
            bone.rotation_quaternion = q
            previous[bone.name] = q.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=bone.name)
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
    path = OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    report['clips'][clip] = {'source_seconds': duration, 'fbx': str(path)}
    print('AXE_RIGHT_ELBOW_EXPORTED', clip, flush=True)

action = bpy.data.actions['A_Harvest_Axe_HitRecover']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_end = 132
scene.frame_set(0)
blend = HERE/'Axe_RightArm_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report['blend'] = str(blend)
(HERE/'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('AXE_RIGHT_ARM_AUTHORED', flush=True)
