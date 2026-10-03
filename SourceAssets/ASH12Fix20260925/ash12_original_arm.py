"""ASH-12 empty reload: keep the optimized hand, restore the ORIGINAL arm handling.

Fourth round of user feedback: bending the elbow by search and forcing the limb straight
were both rejected. The request is now explicit -

    "keep the optimized hand part, look at how the original arm was handled and just
     connect that original arm to it sensibly".

So this pass keeps exactly what was accepted and rebuilds only the right arm chain:

  * the hand keeps its optimized world matrix (the accepted right-edge approach, the
    grip on the charging handle, the mechanical contact, the timing) - untouched;
  * clavicle/arm root come from the ORIGINAL animation (`ASH12_Reference_reload_empty`)
    matrix for matrix, so the shoulder sits where the original animation put it instead
    of on the 23 cm right-shifted root the right-edge pass introduced (that shift is what
    pushed the upper arm through the upper-right near field);
  * the elbow is the exact two-bone solution on the ORIGINAL bend plane, so the elbow
    keeps the original handling instead of a searched pole or a forced straight limb;
  * both bones are re-aimed from the ORIGINAL rotations with the minimal swing needed to
    point at the new elbow/wrist, so the humerus and forearm roll (twist) stay the
    original ones and the wrist joins the preserved hand without a twist at the seam.
  * every other channel (hand, fingers, left arm, weapon, body) is copied from the clip
    currently shipped in the game, so the only difference is the arm.

Bone lengths are exact by construction; the hand world matrix is preserved to 1e-5 cm.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEY = ARGS[0] if ARGS else 'reload_empty'
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883

# base = the clip shipped before this round (the accepted right-edge hand on the rejected
# straight-arm build, itself retired to the task archive); reference = the pre-modification
# original arm, which lives in the same blend's action library.
ARCHIVE = HERE.parents[1] / 'trash/ash12-reload-melee-superseded-20260925'
BLENDS = {
    'reload_empty': (ARCHIVE / 'Blends/ASH12_ReloadEmpty_CameraGuard_StraightArm.blend',
                     'ASH12_EmptyReload_RightEdgeReachPullReturn',
                     'ASH12_ReloadEmpty_OriginalArm'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    BLENDS[f'{family}/reload_empty'] = (
        ARCHIVE / f'Blends/ASH12_{family}_ReloadEmpty_CameraGuard_StraightArm.blend',
        f'ASH12_{family}_reload_empty', f'ASH12_{family}_ReloadEmpty_OriginalArm')
BLEND, ACTION, STEM = BLENDS[KEY]
if 'guard' in ARGS:
    STEM += '_GuardedArm'
REF_ACTION = 'ASH12_Reference_reload_empty'
FRAMES, FPS = 198, 60
# bones whose world transform is taken over / re-derived; everything else is copied
TAKE = ['clavicle_r']
EDIT = ['clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r', 'upperarm_twist_01_r',
        'upperarm_twist_02_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r']
PROBE = (0, 60, 116, 120, 124, 132, 140, 148, 156, 164, 172, 180, 190, 198)


def sample(rig, act, names):
    """All bone world matrices for every frame of one action."""
    out = []
    for f in range(FRAMES + 1):
        rig.animation_data.action = act
        rig.animation_data.action_slot = act.slots[0]
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        out.append({n: rig.pose.bones[n].matrix.copy() for n in names})
    return out


bpy.ops.wm.open_mainfile(filepath=str(BLEND), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
source = bpy.data.actions[ACTION]
reference = bpy.data.actions[REF_ACTION]
for ob in list(bpy.context.scene.objects):
    if ob.type == 'MESH' and ob is not arms:
        ob.hide_viewport = True
        ob.hide_render = True
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
lr = {n: (rest[parents[n]].inverted() @ rest[n]) for n in rest if parents[n]}
NAMES = list(rest.keys())
# a body bone kept as a control: if it matches in both actions the rig root agrees and
# the clavicle world matrix can be carried over without re-basing.
CONTROL = next((n for n in ('spine_03', 'spine_02', 'pelvis', 'root') if n in rest), 'root')
poses = sample(rig, source, NAMES)
ref_poses = sample(rig, reference, NAMES)
surface = SkinSurface(rig, arms)
print('BASE', KEY, ACTION, 'REF', REF_ACTION, 'control', CONTROL, flush=True)
print('BODY_DRIFT_CM', round(max((poses[f][CONTROL].translation
                                  - ref_poses[f][CONTROL].translation).length
                                 for f in range(FRAMES + 1)) * 100, 3), flush=True)

UN, FN, HN, CN = 'upperarm_r', 'lowerarm_r', 'hand_r', 'clavicle_r'
L1 = (rest[FN].translation - rest[UN].translation).length
L2 = (rest[HN].translation - rest[FN].translation).length


def solve(pose, ref, f, blend=0.0):
    """Original arm root + original bend plane, joined to the preserved hand.

    `blend` mixes the bend plane from the original one (0.0) towards the plane that puts
    the elbow as far from the eye as the exact two-bone circle allows (1.0). The bend
    angle itself is fixed by the preserved hand and the bone lengths, so it never changes
    with the plane; only which side the elbow sits on does.
    """
    p = {n: m.copy() for n, m in pose.items()}
    H = pose[HN].copy()                      # the accepted (optimized) hand, untouched
    T = H.translation.copy()
    p[CN] = ref[CN].copy()                   # original arm root, matrix for matrix
    A = ref[UN].translation.copy()
    reach = L1 + L2 - 0.002
    if (T - A).length > reach:               # only if the optimized hand is out of reach
        A = T + (A - T).normalized() * reach
        p[CN].translation = p[CN].translation + (A - ref[UN].translation)
    axis = (T - A).normalized()
    dist = (T - A).length
    along = (L1 * L1 - L2 * L2 + dist * dist) / (2 * max(dist, 1e-6))
    h = math.sqrt(max(0.0, L1 * L1 - along * along))
    # the original bend plane, carried over to the new shoulder->hand axis
    ref_arm = ref[FN].translation - ref[UN].translation
    pole = ref_arm - axis * ref_arm.dot(axis)
    if pole.length < 1e-9:
        pole = pose[FN].translation - pose[UN].translation - axis * (pose[FN].translation
                                                                    - pose[UN].translation).dot(axis)
    pole = pole.normalized() if pole.length > 1e-9 else Vector((0.0, 0.0, 1.0))
    if blend > 0.0:
        # the elbow rides a circle of radius h around the axis midpoint; of all of its
        # points, the one facing away from the eye is the farthest from the lens.
        radial = (A + axis * along) - CAM
        radial = radial - axis * radial.dot(axis)
        if radial.length > 1e-6:
            far = radial.normalized()
            pole = (pole * (1.0 - blend) + far * blend)
            pole = pole.normalized() if pole.length > 1e-9 else far
    E = A + axis * along + pole * h
    # aim each bone from the ORIGINAL rotation with the minimal swing to the new target,
    # so the original humerus/forearm roll (twist) survives the reconnect.
    ref_dir_u = (ref[FN].translation - ref[UN].translation).normalized()
    ref_dir_f = (ref[HN].translation - ref[FN].translation).normalized()
    uq = ref_dir_u.rotation_difference((E - A).normalized()) @ ref[UN].to_quaternion()
    fq = ref_dir_f.rotation_difference((T - E).normalized()) @ ref[FN].to_quaternion()
    for name, origin, q in ((UN, A, uq), (FN, E, fq)):
        p[name] = Matrix.LocRotScale(origin, q, pose[name].to_scale())
        for suffix in ('01', '02'):
            twist = f"{'upperarm' if name == UN else 'lowerarm'}_twist_{suffix}_r"
            if twist in p:
                p[twist] = p[name] @ pose[name].inverted() @ pose[twist]
    p[HN] = H
    return p


RIGHT_ROWS = None


def visible_eye_m(pose):
    """Closest distance from the eye to visible right-side skin (None = nothing visible).

    This, not the forward depth, is the measure of "the limb is in the lens": skin 1 cm
    in front of the eye but 20 cm to the side is harmless, skin 6 cm dead ahead is not.
    """
    global RIGHT_ROWS
    if RIGHT_ROWS is None:
        RIGHT_ROWS = np.flatnonzero(surface.sides == 'r')
    pts = surface.positions(pose)[RIGHT_ROWS] - np.array([CAM.x, CAM.y, CAM.z])
    fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    return float(np.linalg.norm(pts[on], axis=1).min()) if on.any() else None


def clearance(pose):
    pts = surface.positions(pose)[np.flatnonzero(surface.sides == 'r')] - np.array([CAM.x, CAM.y, CAM.z])
    fwd, right, up = pts[:, 1], pts[:, 0], pts[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    return float(fwd[on].min()) if on.any() else None


def bend(pose):
    A = pose[UN].translation
    E = pose[FN].translation
    T = pose[HN].translation
    return math.degrees(math.acos(max(-1.0, min(1.0,
        (E - A).normalized().dot((T - E).normalized())))))


def cs(p):
    d = Vector(p) - CAM
    return [round(d.x * 100, 1), round(d.y * 100, 1), round(d.z * 100, 1)]


fixed = [solve(poses[f], ref_poses[f], f) for f in range(FRAMES + 1)]

# With the corrected hand the original shoulder->hand span is longer than the original
# animation ever asked for, so on 36 frames (130-165) the original bend plane carries the
# elbow across the lens. The plane is then blended towards the far side of the exact
# two-bone circle - just enough, smoothly, to keep the limb out of the lens - so the root,
# the bend angles, the bone rolls and the hand all stay original/optimized. Reported for
# every frame: the blend, the plane deviation and the resulting eye distance.
GUARD = 'guard' in ARGS
LO, HI = 0.12, 0.20                 # eye distance (m) at which the plane starts/fully swings
guard_blend = [0.0] * (FRAMES + 1)
if GUARD:
    for f in range(FRAMES + 1):
        d0 = visible_eye_m(fixed[f])
        if d0 is None or d0 >= HI:
            continue
        t = 1.0 if d0 <= LO else (HI - d0) / (HI - LO)
        guard_blend[f] = t
    fixed = [solve(poses[f], ref_poses[f], f, guard_blend[f]) for f in range(FRAMES + 1)]
    eyes = [visible_eye_m(fixed[f]) for f in range(FRAMES + 1)]
    worst = sorted((v, f) for f, v in enumerate(eyes) if v is not None)[:6]
    print('GUARD', KEY, 'swung_frames', sum(1 for v in guard_blend if v > 0.01),
          'max_blend', round(max(guard_blend), 3),
          'eye_cm', [None if eyes[f] is None else round(eyes[f] * 100, 1) for f in PROBE],
          'worst', [(f, round(v * 100, 1)) for v, f in worst], flush=True)
    guard_deg = [round(math.degrees(math.acos(max(-1.0, min(1.0, 1.0 - v)))), 1)
                 for v in guard_blend]

print('ORIG', KEY, 'bend base', [round(bend(poses[f]), 1) for f in PROBE],
      'orig', [round(bend(ref_poses[f]), 1) for f in PROBE],
      'new', [round(bend(fixed[f]), 1) for f in PROBE], flush=True)
print('ORIG', KEY, 'closest_cm base',
      [None if clearance(poses[f]) is None else round(clearance(poses[f]) * 100, 1) for f in PROBE],
      'ref', [None if clearance(ref_poses[f]) is None else round(clearance(ref_poses[f]) * 100, 1) for f in PROBE],
      'new', [None if clearance(fixed[f]) is None else round(clearance(fixed[f]) * 100, 1) for f in PROBE],
      flush=True)
print('ORIG', KEY, 'arm_root_cm base', [cs(poses[f][UN].translation) for f in PROBE],
      'ref', [cs(ref_poses[f][UN].translation) for f in PROBE], flush=True)
print('ORIG', KEY, 'elbow_cm ref', [cs(ref_poses[f][FN].translation) for f in PROBE],
      'new', [cs(fixed[f][FN].translation) for f in PROBE], flush=True)
print('ORIG', KEY, 'hand_delta_mm', round(max((fixed[f][HN].translation
                                               - poses[f][HN].translation).length
                                              for f in range(FRAMES + 1)) * 1000, 5),
      'bone_len_delta_mm', round(max(abs((fixed[f][FN].translation - fixed[f][UN].translation).length - L1)
                                     + abs((fixed[f][HN].translation - fixed[f][FN].translation).length - L2)
                                     for f in range(FRAMES + 1)) * 1000, 6), flush=True)

action = source.copy()
source.name = 'BASELINE_' + source.name
source.use_fake_user = True
action.name = ACTION
action.use_fake_user = True
curves = {(c.data_path, c.array_index): c
          for layer in action.layers for strip in layer.strips
          for bag in strip.channelbags for c in bag.fcurves}
for name in EDIT:
    rows = [(lr[name].inverted() @ (fixed[f][parents[name]].inverted() @ fixed[f][name])).decompose()
            for f in range(FRAMES + 1)]
    for prop, index, count in (('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)):
        path = f'pose.bones["{name}"].{prop}'
        values, last = [], None
        for f in range(FRAMES + 1):
            v = rows[f][index].copy()
            if prop == 'rotation_quaternion':
                if last is not None and last.dot(v) < 0:
                    v.negate()
                last = v.copy()
            values.append(v)
        for j in range(count):
            curve = curves[(path, j)]
            curve.keyframe_points.clear()
            curve.keyframe_points.add(FRAMES + 1)
            curve.keyframe_points.foreach_set('co', [v for f, row in enumerate(values) for v in (f, row[j])])
            for k in curve.keyframe_points:
                k.interpolation = 'LINEAR'
            curve.update()
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene = bpy.context.scene
scene.render.fps = FPS
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = 0, FRAMES
scene.frame_set(140)
bpy.context.view_layer.update()
out_blend = HERE / 'Blends' / f'{STEM}.blend'
out_fbx = HERE / 'Animations' / f'{ACTION}.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
for ob in scene.objects:
    ob.select_set(ob is rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={'ARMATURE'},
                         axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                         bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_force_startend_keying=True, bake_anim_step=1,
                         bake_anim_simplify_factor=0)
report = dict(key=KEY, base_blend=str(BLEND), action=ACTION, arm_reference=REF_ACTION,
              hand_source='shipped optimized hand (right-edge approach)',
              guard=GUARD, guard_eye_floor_cm=LO * 100, guard_eye_full_cm=HI * 100,
              guard_plane_deviation_deg=guard_deg,
              body_drift_cm=round(max((poses[f][CONTROL].translation
                                       - ref_poses[f][CONTROL].translation).length
                                      for f in range(FRAMES + 1)) * 100, 4),
              bend_base={str(f): round(bend(poses[f]), 2) for f in range(FRAMES + 1)},
              bend_reference={str(f): round(bend(ref_poses[f]), 2) for f in range(FRAMES + 1)},
              bend_new={str(f): round(bend(fixed[f]), 2) for f in range(FRAMES + 1)},
              closest_base_cm={str(f): (None if clearance(poses[f]) is None else round(clearance(poses[f]) * 100, 1))
                               for f in range(FRAMES + 1)},
              closest_new_cm={str(f): (None if clearance(fixed[f]) is None else round(clearance(fixed[f]) * 100, 1))
                              for f in range(FRAMES + 1)},
              hand_world_delta_mm=round(max((fixed[f][HN].translation
                                             - poses[f][HN].translation).length
                                            for f in range(FRAMES + 1)) * 1000, 5),
              out_blend=str(out_blend), out_fbx=str(out_fbx), game_tested=False)
(HERE / f'original_arm_{KEY.replace("/", "_")}.json').write_text(json.dumps(report, indent=2))
print('ORIGINAL_ARM_WROTE', str(out_blend), str(out_fbx), flush=True)
