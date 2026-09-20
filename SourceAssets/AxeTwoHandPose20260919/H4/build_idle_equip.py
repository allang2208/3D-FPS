"""H4 two-hand hold and equip, built from the actual H3 pose and breathing.

Keep the tool-local wrists, finger shapes, skin and full forearm segments.
Only author/export; no renders, playback tests or acceptance probes.
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CFG = json.loads((HERE / 'pose.json').read_text(encoding='utf-8'))
SOURCE = json.loads((ROOT / 'SourceAssets/KimodoAxeIdle20260919/BuildH3/authoring.json').read_text(encoding='utf-8'))
IDLE = dict(SOURCE['config'])
OUT = HERE / 'Export'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SOURCE['blend'])
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
source_action = bpy.data.actions[IDLE['name']]
rig.animation_data.action = source_action
rig.animation_data.action_slot = source_action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
old_idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
old_ready = old_idle['WPN_root']
grips = {s: old_ready.inverted() @ old_idle['hand_' + s] for s in ('r', 'l')}
fingers = {s: {b.name: old_idle['hand_' + s].inverted() @ old_idle[b.name] for b in rig.data.bones
               if b.name.endswith('_' + s) and b.name.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))}
           for s in ('r', 'l')}
center = (old_idle['hand_r'].translation + old_idle['hand_l'].translation) * .5
tilt = Matrix.Rotation(math.radians(-CFG['tilt_degrees']), 4, 'Y')
shift = Matrix.Translation(center) @ tilt @ Matrix.Translation(-center)
ready = shift @ old_ready
# Read H3's existing motion before creating the replacement action.
idle_frames = []
for f in range(round(CFG['idle_seconds'] * CFG['fps']) + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    idle_frames.append(shift @ rig.pose.bones['WPN_root'].matrix.copy())


def ease(t):
    t = min(1., max(0., t))
    return t*t*t*(10.-15.*t+6.*t*t)


def solve_arm(pose, side, hand):
    upper, fore, wrist = [n + '_' + side for n in ('upperarm', 'lowerarm', 'hand')]
    shoulder = rest[upper].translation + Vector((0, IDLE['shoulder_forward_m'], -IDLE['shoulder_down_m']))
    target = hand.translation
    l1 = (rest[fore].translation - rest[upper].translation).length
    l2 = (rest[wrist].translation - rest[fore].translation).length
    reach = target - shoulder
    direction = reach.normalized()
    shoulder += direction * max(0., reach.length - IDLE['reach_fraction']*(l1+l2))
    distance = (target - shoulder).length
    down = Vector((IDLE['elbow_outward']*(1 if side == 'r' else -1), IDLE['elbow_backward'], -1))
    pole = (down - direction*down.dot(direction)).normalized()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow = shoulder + direction*along + pole*math.sqrt(max(0., l1*l1-along*along))
    original_upper = (rest[fore].translation-rest[upper].translation).normalized()
    original_fore = (rest[wrist].translation-rest[fore].translation).normalized()
    upper_q = original_upper.rotation_difference((elbow-shoulder).normalized()) @ rest[upper].to_quaternion()
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    fore_deform = (hand_deform @ original_fore).rotation_difference((target-elbow).normalized()) @ hand_deform
    pose['clavicle_' + side].translation += shoulder-rest[upper].translation
    pose[upper] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
    pose[fore] = Matrix.LocRotScale(elbow, fore_deform @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
    for segment in (upper, fore):
        for index in ('01', '02'):
            helper = segment.replace('_' + side, '_twist_' + index + '_' + side)
            if helper in rest:
                pose[helper] = pose[segment] @ rest[segment].inverted() @ rest[helper]
    pose[wrist] = hand
    for b in rig.pose.bones:
        if b.name in fingers[side]:
            position = pose[b.parent.name] @ local_rest[b.name].translation
            rotation = hand.to_quaternion() @ fingers[side][b.name].to_quaternion()
            pose[b.name] = Matrix.LocRotScale(position, rotation, Vector((1, 1, 1)))


def equip_frame(t):
    if t <= CFG['equip_raise_seconds']:
        u = ease(t / CFG['equip_raise_seconds'])
        offset = Vector(CFG['equip_start_offset_m']).lerp(Vector(CFG['equip_settle_offset_m']), u)
        angle = CFG['equip_start_pitch_degrees']*(1-u) + CFG['equip_settle_pitch_degrees']*u
    else:
        u = ease((t-CFG['equip_raise_seconds'])/(CFG['equip_seconds']-CFG['equip_raise_seconds']))
        offset = Vector(CFG['equip_settle_offset_m'])*(1-u)
        angle = CFG['equip_settle_pitch_degrees']*(1-u)
    rotate = Matrix.Rotation(math.radians(angle), 4, 'X')
    return Matrix.Translation(center+offset) @ rotate @ Matrix.Translation(-center) @ ready


clips = {}
for clip, duration in (('Idle', CFG['idle_seconds']), ('Equip', CFG['equip_seconds'])):
    name = 'A_Harvest_Axe_' + clip
    old = bpy.data.actions.get(name)
    if old:
        old.name = 'REF_PreH4_' + name
        old.use_fake_user = True
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps = CFG['fps']
    scene.render.fps_base = 1
    scene.frame_start = 0
    scene.frame_end = round(duration * CFG['fps'])
    previous_quats = {}
    for f in range(scene.frame_end + 1):
        scene.frame_set(f)
        wpn = idle_frames[f] if clip == 'Idle' else equip_frame(f / CFG['fps'])
        pose = {n: m.copy() for n, m in rest.items()}
        for side in ('r', 'l'):
            solve_arm(pose, side, wpn @ grips[side])
        pose['WPN_root'] = wpn
        for b in rig.pose.bones:
            parent_inv = pose[b.parent.name].inverted() if b.parent else Matrix.Identity(4)
            b.matrix_basis = local_rest[b.name].inverted() @ parent_inv @ pose[b.name]
        bpy.context.view_layer.update()
        for b in rig.pose.bones:
            b.rotation_mode = 'QUATERNION'
            q = b.rotation_quaternion.copy()
            if b.name in previous_quats and q.dot(previous_quats[b.name]) < 0:
                q.negate()
            b.rotation_quaternion = q
            previous_quats[b.name] = q.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                b.keyframe_insert(channel, frame=f, group=b.name)
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
    path = OUT / (name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
                            axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    clips[clip] = {'fbx': str(path), 'source_seconds': duration}
    print('AXE_H4_EXPORTED ' + clip, flush=True)

rig.animation_data.action = bpy.data.actions['A_Harvest_Axe_Idle']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_end = round(CFG['idle_seconds'] * CFG['fps'])
scene.frame_set(0)
bpy.ops.file.pack_all()
blend = HERE / 'Axe_TwoHand_H4_Idle_Equip_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
IDLE.update(name='A_Harvest_Axe_Idle', revision=CFG['revision'], fps=CFG['fps'],
            duration_s=CFG['idle_seconds'], handle_lean_deg=IDLE['handle_lean_deg']+CFG['tilt_degrees'],
            hold_origin_m=list(ready.translation))
report = {'runtime_tested': False, 'rendered': False, 'source': SOURCE['blend'], 'config': IDLE,
          'pose_config': CFG, 'blend': str(blend), 'clips': clips,
          'contacts': {s: {'tool_local_hand': [list(row) for row in grips[s]],
                           'height_change_m': (ready @ grips[s]).translation.z-old_idle['hand_'+s].translation.z}
                       for s in ('r', 'l')}}
(HERE / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('AXE_H4_IDLE_EQUIP_AUTHORED', flush=True)
