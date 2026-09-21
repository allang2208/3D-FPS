"""Extend after the spin, then settle; retain the existing baked V5 lead-in.

Uses the authored V5 pose as the arm reference at every sample. Both hands
travel with the weapon; fixed-length IK carries forearm roll, helpers and
fingers together. This builds editable animation, without rendering a preview.
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parents[1]
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'MeleePommelAttack20260916'))
sys.path.insert(0, str(P.parent / 'ImpactV5'))
import whirlwind_motion as motion
from pommel_motion import shaft

FPS = motion.FPS
START = motion.SPIN_END
END = motion.ATTACK_END
SOURCE = P.parent / 'ImpactV5/Whirlwind_Manny_Editable.blend'
NAME = 'A_RuneSword_WhirlwindRecoverV6'

# Camera space is Blender +Y forward, +X right, +Z up. The reference's
# diagonal blade points forward/up-right while the hilt is sent away from
# the chest. These are reconstructed 3D targets, not extracted motion data.
EXTEND = shaft((.50, .74, .45), (-.075, .49, -.155), 25)
UNLOAD = shaft((.48, .72, .50), (-.06, .485, -.165), 25)
motion.KNOTS = [START, START + .18, START + .24, END]
motion.KEYS = [motion.FOLLOW, EXTEND, UNLOAD, motion.IDLE]
motion.BASE = motion.KEYS[0][0].to_quaternion()
motion.POSITIONS = [g.translation.copy() for g, s in motion.KEYS]
motion.ROTATIONS = [motion.rotation_vector(motion.BASE.inverted() @ g.to_quaternion()) for g, s in motion.KEYS]
motion.FACES = [motion.rotation_vector(g.to_quaternion().inverted() @ s.to_quaternion()) for g, s in motion.KEYS]
motion.POSITION_VELOCITY = motion.tangents(motion.POSITIONS)
motion.ROTATION_VELOCITY = motion.tangents(motion.ROTATIONS)
motion.FACE_VELOCITY = motion.tangents(motion.FACES)

def smooth(t):
    t = max(0., min(1., t))
    return t*t*t*(10 + t*(-15 + 6*t))

def blended(a, b, weight):
    ap, aq, asc = a.decompose()
    bp, bq, bsc = b.decompose()
    return Matrix.LocRotScale(ap.lerp(bp, weight), aq.slerp(bq, weight), asc.lerp(bsc, weight))

def carry_arm(original, desired, side, delta):
    clav, upper, lower, hand = [n + '_' + side for n in ['clavicle', 'upperarm', 'lowerarm', 'hand']]
    a, e, w = [original[n].translation.copy() for n in [upper, lower, hand]]
    target = delta @ original[hand]
    end = target.translation
    l1, l2 = (e-a).length, (w-e).length
    axis = (end-a).normalized()
    distance = (end-a).length
    # Retain elbow reserve by moving the shoulder only when required; the
    # wrist stays on the shared grip rather than being clamped off the hilt.
    reach = l1 + l2 - .018
    if distance > reach:
        a += axis * (distance-reach)
    distance = max(1e-7, (end-a).length)
    axis = (end-a).normalized()
    pole = (e-a) - axis * (e-a).dot(axis)
    if pole.length < 1e-6:
        pole = axis.cross(Vector((1, 0, 0)))
    along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
    height = math.sqrt(max(0., l1*l1 - along*along))
    elbow = a + axis*along + pole.normalized()*height
    uq = (original[lower].translation-original[upper].translation).rotation_difference(elbow-a) @ original[upper].to_quaternion()
    # Carry the grip's roll into the forearm before aligning its long axis.
    dq = delta.to_quaternion()
    old_fore = original[hand].translation-original[lower].translation
    fq = (dq @ old_fore).rotation_difference(end-elbow) @ dq @ original[lower].to_quaternion()
    desired[clav] = original[clav].copy()
    desired[clav].translation += a-original[upper].translation
    desired[upper] = Matrix.LocRotScale(a, uq, original[upper].to_scale())
    desired[lower] = Matrix.LocRotScale(elbow, fq, original[lower].to_scale())
    desired[hand] = target

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
bones = list(rig.data.bones)
rest = {b.name: b.matrix_local.copy() for b in bones}
localrest = {b.name: (rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]) for b in bones}
frames = round(END*FPS)
explicit = {'WPN_root'} | {n+'_'+s for s in ['l', 'r'] for n in ['clavicle', 'upperarm', 'lowerarm', 'hand']}
affected = set(explicit)
for b in bones:
    if any(p.name in affected for p in b.parent_recursive):
        affected.add(b.name)
baked = []
for frame in range(frames+1):
    scene.frame_set(frame)
    original = {b.name: b.matrix.copy() for b in rig.pose.bones}
    pose = {n: m.copy() for n, m in original.items()}
    t = frame/FPS
    if START < t < END:
        target = motion.poses(t)[1]
        # Join onto the actual V5 velocity, with zero first/second derivative
        # of the correction at the boundary, rather than re-solving its spin.
        weapon = blended(original['WPN_root'], target, smooth((t-START)/.065))
        delta = weapon @ original['WPN_root'].inverted()
        pose['WPN_root'] = weapon
        for side in ['l', 'r']:
            carry_arm(original, pose, side, delta)
        # Preserve each auxiliary/finger bone's authored parent transform.
        # WPN_root is independent even if the skeleton parents it to a hand.
        for b in bones:
            if b.name not in explicit and b.parent and b.name in affected:
                pose[b.name] = pose[b.parent.name] @ original[b.parent.name].inverted() @ original[b.name]
    local = {}
    for b in bones:
        basis = localrest[b.name].inverted() @ (pose[b.parent.name].inverted() @ pose[b.name] if b.parent else pose[b.name])
        local[b.name] = basis.decompose()
    baked.append(local)

action = bpy.data.actions.new(NAME)
action.use_fake_user = True
rig.animation_data.action = action
scene.render.fps = FPS
scene.render.fps_base = 1
scene.frame_start = 0
scene.frame_end = frames
previous = {}
for frame, local in enumerate(baked):
    scene.frame_set(frame)
    for b in rig.pose.bones:
        loc, q, scale = local[b.name]
        if b.name in previous and q.dot(previous[b.name]) < 0:
            q.negate()
        b.rotation_mode = 'QUATERNION'
        b.location, b.rotation_quaternion, b.scale = loc, q, scale
        previous[b.name] = q.copy()
        b.keyframe_insert('location', frame=frame, group=b.name)
        b.keyframe_insert('rotation_quaternion', frame=frame, group=b.name)
        b.keyframe_insert('scale', frame=frame, group=b.name)

bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(OUT/(NAME+'.fbx')), use_selection=True,
    object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0)
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'WhirlwindRecover_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({
    'clip': NAME, 'source': str(SOURCE), 'fps': FPS, 'intervals': frames,
    'recover_start_seconds': START, 'recover_seconds': END-START,
    'extend_seconds': START+.18, 'unload_seconds': START+.24,
    'end_seconds': END, 'knots_seconds': motion.KNOTS,
    'affected_bones': sorted(affected), 'loop': False,
    'reference': 'BV18b4y1774T 183.33-183.50 seconds; reconstructed 3D reach',
    'tested': False}, indent=2), encoding='utf-8')
print('WHIRLWIND_RECOVER_AUTHORED', flush=True)
