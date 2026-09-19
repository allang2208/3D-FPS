"""ASH-12 reloads adapted from the user's Saved/Ash12ReloadRef/ref.mp4.

Reference: 30 fps; 6.50-6.93 release/drop, 6.93-7.30 offscreen retrieval,
7.43-7.77 new magazine insertion, 8.10-8.40 overhand charging, then recovery.
Only the empty action is visible. The tactical action adapts the common swap
and goes directly back to the grip. Durations are deliberate gameplay pacing,
not a claim that a 2D video has yielded exact 3D motion.

Reads the existing fitted mesh/rest/materials, authors two new clips, and saves
an editable copy. No mesh, bind pose, weights, ADS or equip animation changes.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
from arm_ik import shift_arm_natural

SOURCE = OUT.parent / 'ASH1220260917/ASH12_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
gun = bpy.data.objects['ASH12_Export']
idle = bpy.data.actions['ASH12_idle']
rig.animation_data.action = idle
if idle.slots:
    rig.animation_data.action_slot = idle.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
names = [b.name for b in rig.data.bones]
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n] for n in names}
base = {b.name: b.matrix.copy() for b in rig.pose.bones}
base_basis = {n: local_rest[n].inverted() @ (base[parents[n]].inverted() @ base[n] if parents[n] else base[n]) for n in names}


def descendants(root):
    return [root] + [n for b in rig.data.bones[root].children for n in descendants(b.name)]


def hand_subtree(side):
    return descendants('hand_' + side)


def smooth(x):
    x = max(0., min(1., x))
    return x * x * x * (x * (x * 6. - 15.) + 10.)


def curve(keys, t):
    if t <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            w = smooth((t - a[0]) / (b[0] - a[0]))
            return tuple(x + (y - x) * w for x, y in zip(a[1:], b[1:]))
    return keys[-1][1:]


def key(t, v):
    return (t, *v)


def blend_transform(a, b, w):
    p, q, s = a.decompose()
    p1, q1, s1 = b.decompose()
    return Matrix.LocRotScale(p.lerp(p1, w), q.slerp(q1, w), s.lerp(s1, w))


ROOT = base['WPN_root']
inv = ROOT.inverted()
receiver_local = {n: inv @ base[n] for n in descendants('WPN_root')}
grip = inv @ base['hand_r']
support = inv @ base['hand_l']
mag0 = receiver_local['WPN_SOCKET_Magazine']
handle0 = receiver_local['WPN_ChargingHandle']
bolt0 = receiver_local['WPN_bolt']
# MCP positions stay fixed while their children curl; use the palm's knuckle
# line to locate a broad magazine grasp rather than aiming one fingertip.
knuckle = sum((inv @ base[n].translation for n in ['index_01_r', 'middle_01_r', 'ring_01_r']), Vector()) / 3 - grip.translation
mag_hand = grip.copy()
mag_hand.translation = mag0.translation + Vector((.006, .008, -.100)) - knuckle

# Measure the REAL tab in the reference mesh. Its bone origin is elsewhere.
group = gun.vertex_groups['WPN_ChargingHandle']
rest_inv = rest['WPN_root'].inverted()
tab = [rest_inv @ (gun.matrix_world @ v.co) for v in gun.data.vertices
       if any(g.group == group.index and g.weight > .5 for g in v.groups)]
top = max(v.z for v in tab)
patch = [v for v in tab if v.z > top - .010]
outside = min(v.x for v in patch)
patch = [v for v in patch if v.x < outside + .004]
contact = sum(patch, Vector()) / len(patch)
overhand = Matrix.Rotation(math.radians(80), 4, 'Y')
handle_hand = overhand @ grip
handle_hand.translation = contact - overhand.to_3x3() @ knuckle + Vector((-.005, .004, .006))

DURATIONS = {'reload': 2.4, 'reload_empty': 3.3}
CUES = {'out': .36, 'insert': 1.56, 'seat': 1.86, 'pull': 2.34, 'bolt': 2.60}
OLD_GONE, NEW_ENTER = .84, 1.05
# Both old and replacement meshes are outside the view during this changeover.
# No bone scaling and no teleport while the magazine is being carried on screen.
mag_new_offset = Vector((-.24, .10, -.18))
offhand = mag_hand.translation + mag_new_offset
mid_hand = Vector((-.115, .105, -.045))

FINGER_CURL = {
    'open': {'index': (12, 22, 8), 'middle': (18, 20, 9), 'ring': (20, 23, 10), 'pinky': (24, 25, 12)},
    'mag': {'index': (58, 62, 31), 'middle': (60, 63, 34), 'ring': (56, 59, 31), 'pinky': (52, 55, 28)},
    'handle': {'index': (46, 70, 34), 'middle': (52, 66, 32), 'ring': (48, 56, 27), 'pinky': (44, 50, 24)},
}


def hand_profile(t, empty):
    # Open before contact; close the palm on the replacement; release only
    # after seating. Index leads, ring/pinky trail by a few authoring samples.
    tail = [(2.12, 1, 0, 0), (2.32, 0, 0, 1), (2.59, 0, 0, 1),
            (2.70, 1, 0, 0), (3.03, 0, 0, 0), (3.3, 0, 0, 0)] if empty else [
            (2.14, 1, 0, 0), (2.28, 0, 0, 0), (2.4, 0, 0, 0)]
    return curve([(0, 0, 0, 0), (.12, 1, 0, 0), (.31, .35, .65, 0),
                  (.39, .35, .65, 0), (.57, 1, 0, 0), (.94, 1, 0, 0),
                  (1.04, 0, 1, 0), (1.87, 0, 1, 0), (2.05, 1, 0, 0)] + tail, t)


def fingers(pose, t, empty):
    lag = {'index': 0., 'middle': .008, 'ring': .020, 'pinky': .032, 'thumb': .012}
    for n in hand_subtree('r')[1:]:
        local = base_basis[n].copy()
        parts = n.split('_')
        if len(parts) == 3 and parts[1] in ('01', '02', '03') and parts[0] in lag:
            finger, joint = parts[0], int(parts[1]) - 1
            w_open, w_mag, w_handle = hand_profile(max(0, t - lag[finger] - joint * .004), empty)
            pos, rot, scale = local.decompose()
            e = rot.to_euler('XYZ')
            if finger == 'thumb':
                # Oppose the thumb without relocating its root or metacarpal.
                e.z += math.radians((-14 * w_open + 7 * w_mag + 3 * w_handle) * (1 if joint == 0 else .5))
                if joint == 0:
                    e.y -= math.radians(8 * w_open)
            else:
                original = e.z
                for name, weight in [('open', w_open), ('mag', w_mag), ('handle', w_handle)]:
                    e.z += (math.radians(FINGER_CURL[name][finger][joint]) - original) * weight
            local = Matrix.LocRotScale(pos, e.to_quaternion(), scale)
        # Rebuild in parent order: rotating a knuckle carries every downstream
        # phalanx, preserving all finger lengths and avoiding the old split poses.
        pose[n] = pose[parents[n]] @ local_rest[n] @ local


def magazine(t, W):
    if t < OLD_GONE:
        # Unlock, move axially clear of the well, then let the old magazine fall.
        axial = curve([(0, 0), (.36, 0), (.48, -.12), (OLD_GONE, -.12)], t)[0]
        M = W @ Matrix.Translation((0, 0, axial)) @ mag0
        age = max(0., t - .48)
        M.translation += Vector((.50 * age, -.10 * age, -1.5 * age - 4.9 * age * age))
        M = M @ Matrix.Rotation(math.radians(age * 125), 4, 'X')
        return M
    # Hold the replacement at a reachable offscreen location; the arm and the
    # magazine share exactly one rigid grasp from arrival through seating.
    v = Vector(curve([key(OLD_GONE, mag_new_offset), key(NEW_ENTER, mag_new_offset),
                      (1.28, -.065, .025, -.145), (1.46, -.012, .006, -.108),
                      (1.56, 0, 0, -.085), (1.76, 0, 0, -.014),
                      (1.86, 0, 0, 0), (3.3, 0, 0, 0)], t))
    tilt = curve([(OLD_GONE, -14), (1.28, -8), (1.48, 0), (3.3, 0)], t)[0]
    # Rotate about the magazine itself, not the receiver origin.
    M = mag0.copy()
    M.translation += v
    M = M @ Matrix.Rotation(math.radians(tilt), 4, 'X')
    return W @ M


def sample_action(t, kind):
    D = DURATIONS[kind]
    empty = kind == 'reload_empty'
    # Shoulder clearance is inherited from the existing accepted idle. The
    # magazine stage holds a readable canted silhouette instead of drifting.
    common = [(0, 0, 0, 0, 0, 0), (.18, -2, .4, 28, .003, .003),
              (.36, -4, .6, 64, .007, .008), (.66, -4, .7, 68, .010, .010),
              (1.05, -3.5, .4, 66, .010, .010), (1.56, -4, .7, 68, .012, .012),
              (1.86, -4, .8, 68, .012, .012)]
    tail = [(2.08, -3, .8, 54, .010, .007), (2.34, -2, .6, 46, .008, .004),
            (2.6, -2, .6, 46, .008, .004), (2.85, -1.5, .3, 28, .004, .002),
            (3.16, 0, 0, 0, 0, 0), (D, 0, 0, 0, 0, 0)] if empty else [
            (2.05, -2, .4, 46, .008, .006), (2.28, -.3, 0, 4, .001, .001), (D, 0, 0, 0, 0, 0)]
    pitch, yaw, roll, back, down = curve(common + tail, t)
    W = ROOT @ Matrix.Translation((0, back, -down)) @ Matrix.Rotation(math.radians(roll), 4, 'Y') @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(pitch), 4, 'X')
    # A shaped contact pulse: zero at first contact, a brief peak, then recovery.
    hit = curve([(0, 0), (1.86, 0), (1.89, 1), (1.93, -.22), (2.01, 0), (D, 0)], t)[0]
    W = W @ Matrix.Translation((0, .008 * hit, 0)) @ Matrix.Rotation(math.radians(2.2 * hit), 4, 'X')
    pose = {n: m.copy() for n, m in base.items()}
    for n, local in receiver_local.items():
        pose[n] = W @ local
    M = magazine(t, W)
    pose['WPN_SOCKET_Magazine'] = M
    pull = curve([(0, 0), (2.34, 0), (2.54, .058), (2.60, .058), (2.65, 0), (3.3, 0)], t)[0] if empty else 0
    pose['WPN_ChargingHandle'] = W @ Matrix.Translation((0, pull, 0)) @ handle0
    pose['WPN_bolt'] = W @ Matrix.Translation((0, pull, 0)) @ bolt0
    if t < NEW_ENTER:
        # Brief release gesture, then go out to retrieve. The old magazine
        # leaves independently; the hand does not carry it back into the well.
        p = Vector(curve([key(0, grip.translation), key(.08, grip.translation),
                          key(.30, mag_hand.translation), key(.39, mag_hand.translation),
                          key(.63, offhand), key(NEW_ENTER, offhand)], t))
        H = mag_hand.copy()
        H.translation = p
        if t < .30:
            H = blend_transform(grip, H, smooth(t / .30))
        H = W @ H
        if t >= OLD_GONE:
            grasped = M @ mag0.inverted() @ mag_hand
            H = blend_transform(H, grasped, smooth((t - OLD_GONE) / (NEW_ENTER - OLD_GONE)))
    elif t <= 1.91:
        H = M @ mag0.inverted() @ mag_hand
    else:
        # Leave the seated magazine outward first, avoiding a straight-line
        # cut through the bullpup stock while changing from mag to handle/grip.
        clear = mag_hand.copy()
        clear.translation += Vector((-.060, .012, -.020))
        if empty:
            approach = handle_hand.copy()
            approach.translation += Vector((-.030, .010, .030))
            loaded = handle_hand.copy()
            # Once released, the spring drives the handle forward while the
            # hand withdraws from the rearward grip position independently.
            loaded.translation += Vector((0, pull if t <= 2.60 else .058, 0))
            retreat = handle_hand.copy()
            retreat.translation += Vector((-.080, .025, .035))
            mid = grip.copy()
            mid.translation = mid_hand
            hand_keys = [(1.91, mag_hand), (2.06, clear), (2.20, approach),
                         (2.34, loaded), (2.60, loaded), (2.71, retreat),
                         (2.91, mid), (3.10, grip), (D, grip)]
        else:
            hand_keys = [(1.91, mag_hand), (2.05, clear), (2.27, grip), (D, grip)]
        H = hand_keys[-1][1]
        for (t0, h0), (t1, h1) in zip(hand_keys, hand_keys[1:]):
            if t <= t1:
                H = blend_transform(h0, h1, smooth((t - t0) / (t1 - t0)))
                break
        if empty and 2.34 <= t <= 2.60:
            H = loaded  # Exact hand/handle travel during the pull, no interpolation lag.
        H = W @ H
    envelope = smooth(t / .18) * smooth((D - t) / .18)
    for side, target in [('l', W @ support), ('r', H)]:
        upper, lower = 'upperarm_' + side, 'lowerarm_' + side
        original_pole = base[lower].translation - base[upper].translation
        authored_pole = W.to_quaternion() @ Vector((-.85, .25, -.50)) if side == 'r' else original_pole
        pole = original_pole.lerp(authored_pole, envelope).normalized()
        shift_arm_natural(pose, side, pole, target, .55 * envelope, rest=rest, hand_subtree=hand_subtree)
    fingers(pose, t, empty)
    # Finish at the exact accepted idle, including its helper bones. Contact
    # work is already over before the small terminal blend begins.
    if t < .10 or t > D - .12:
        w = min(smooth(t / .10), smooth((D - t) / .12))
        for n in names:
            pose[n] = blend_transform(base[n], pose[n], w)
    return pose


report = {'reference': 'Saved/Ash12ReloadRef/ref.mp4', 'reference_fps': 30,
          'author_fps': 60, 'sample_rate': 120, 'source_blend': str(SOURCE),
          'contacts_seconds': CUES, 'clips': {}}
for kind, duration in DURATIONS.items():
    action = bpy.data.actions.new('ASH12_Reference_' + kind)
    action.use_fake_user = True
    rig.animation_data.action = action
    previous = {}
    end = int(round(duration * 60))
    for step in range(end * 2 + 1):
        t = step / 120.
        pose = sample_action(t, kind)
        for n in names:
            local = local_rest[n].inverted() @ (pose[parents[n]].inverted() @ pose[n] if parents[n] else pose[n])
            loc, q, scale = local.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            b = rig.pose.bones[n]
            b.rotation_mode = 'QUATERNION'
            b.location, b.rotation_quaternion, b.scale = loc, q, scale
            for prop in ('location', 'rotation_quaternion', 'scale'):
                b.keyframe_insert(prop, frame=step / 2.)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:
                        k.interpolation = 'LINEAR'
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = 0, end
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(OUT / ('A_ASH12_' + kind + '.fbx')),
        use_selection=True, object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
        bake_anim_step=.5, bake_anim_simplify_factor=0)
    report['clips'][kind] = {'duration': duration, 'end_frame': end, 'action': action.name}

rig.animation_data.action = idle
if idle.slots:
    rig.animation_data.action_slot = idle.slots[0]
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ASH12_Reload_Reference_Editable.blend'))
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ASH12_REFERENCE_AUTHOR_COMPLETE', json.dumps(report))
