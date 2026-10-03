"""ASH-12 quick melee: pick the cheapest correction that gets the upper arm out of the lens.

The shipped melee pass fixed the near field by translating arm roots per frame (a 10.1 cm
pop between frames 9 and 10) and, for the grip families, by pushing the whole weapon and
both hands 24 cm forward, which drove the right arm to a reach ratio of 0.996 for frames
8-19: a dead-straight locked limb with the wrist pulled off the solved chain. That is the
"扭曲、闪动、形变" being reported.

This pass leaves the animation itself alone - source roots, source bend angles, source bone
rolls, hands untouched, weapon untouched - and searches, per arm, for the cheapest of two
classic corrections:

  * `rotate`: swing the bend plane about the arm's own axis (elbow rides its exact circle,
    so the elbow angle cannot change);
  * `shift`: translate the arm root (clavicle rigidly following) and re-solve the two-bone
    chain to the untouched wrist.

Candidates are scored on the frames that actually need help, and the winner is the one with
the least elbow travel per frame that still clears the lens, keeps the reach ratio below
saturation and keeps the elbow angle sane. The chosen amount is a single value eased in and
out over RAMP frames - never a per-frame search - so nothing can flicker.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ash12_lib import SkinSurface

S = HERE.parent
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KEY = ARGS[0] if ARGS else 'base'
CAM = Vector((0.0, -0.10, 0.05))
TV75, TH75 = math.tan(math.radians(75 / 2)), math.tan(math.radians(75 / 2)) * 2109 / 883
FRAMES, FPS = 54, 60
LO, HI = 0.13, 0.21            # eye distance (m) where the correction starts / is at full need
TARGET = 0.145                 # clearance the search must reach if it can
RAMP = 6
BLENDS = {
    'base': (S / 'RifleQuickMelee20260919/ASH12/Base/ASH12_QuickCombat_Base_Editable.blend',
             'ASH12_QuickCombat_N_Base', 'ASH12_QuickCombat_Base_PlaneArm'),
}
for family in ('vertical', 'canted', 'prism', 'angled'):
    BLENDS[family] = (S / f'ASH12UniversalAttachments20260919/ASH12_{family}_Grips_Editable.blend',
                      f'ASH12_{family}_QuickCombat', f'ASH12_{family}_QuickCombat_PlaneArm')
BLEND, ACTION, STEM = BLENDS[KEY]
EDIT = {s: [f'clavicle_{s}', f'upperarm_{s}', f'lowerarm_{s}',
            f'upperarm_twist_01_{s}', f'upperarm_twist_02_{s}',
            f'lowerarm_twist_01_{s}', f'lowerarm_twist_02_{s}'] for s in ('r', 'l')}
DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
        (0.71, 0.71, 0), (0.71, -0.71, 0), (-0.71, 0.71, 0), (-0.71, -0.71, 0),
        (0.71, 0, 0.71), (-0.71, 0, 0.71), (0.71, 0, -0.71), (-0.71, 0, -0.71)]
MAGS = (0.04, 0.08, 0.12, 0.16, 0.20, 0.24)

bpy.ops.wm.open_mainfile(filepath=str(BLEND), use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
arms = bpy.data.objects['SK_Manny_Arms_Export']
source = bpy.data.actions[ACTION]
for ob in list(bpy.context.scene.objects):
    if ob.type == 'MESH' and ob is not arms:
        ob.hide_viewport = True
        ob.hide_render = True
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
lr = {n: (rest[parents[n]].inverted() @ rest[n]) for n in rest if parents[n]}
NAMES = list(rest.keys())
poses = []
for f in range(FRAMES + 1):
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    poses.append({n: rig.pose.bones[n].matrix.copy() for n in NAMES})
surface = SkinSurface(rig, arms)
ROWS = {s: np.flatnonzero(surface.sides == s) for s in ('r', 'l')}
LEN = {f'{s}{i}': ((poses[0][f'lowerarm_{s}'].translation - poses[0][f'upperarm_{s}'].translation).length
                   if i == 1 else (poses[0][f'hand_{s}'].translation
                                   - poses[0][f'lowerarm_{s}'].translation).length)
       for s in ('r', 'l') for i in (1, 2)}
REACH = {s: LEN[f'{s}1'] + LEN[f'{s}2'] for s in ('r', 'l')}
pts0 = [surface.positions(p) - np.array([CAM.x, CAM.y, CAM.z]) for p in poses]


def eye_side(pose, side, pts=None):
    if pts is None:
        pts = surface.positions(pose) - np.array([CAM.x, CAM.y, CAM.z])
    sub = pts[ROWS[side]]
    fwd, right, up = sub[:, 1], sub[:, 0], sub[:, 2]
    on = (fwd > 0.006) & (np.abs(right) <= TH75 * fwd) & (np.abs(up) <= TV75 * fwd)
    return float(np.linalg.norm(sub[on], axis=1).min()) if on.any() else None


def solve_side(pose, side, delta=0.0, shift=None):
    """Re-aim one two-bone chain; wrist preserved, root optionally slid, elbow angle fixed."""
    p = {n: m.copy() for n, m in pose.items()}
    cn, un, fn, hn = f'clavicle_{side}', f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}'
    T = pose[hn].translation.copy()
    A = pose[un].translation.copy()
    if shift is not None:
        A = A + shift
        p[cn] = pose[cn].copy()
        p[cn].translation = p[cn].translation + shift
    l1, l2 = LEN[f'{side}1'], LEN[f'{side}2']
    axis = (T - A).normalized()
    dist = (T - A).length
    if dist > l1 + l2 - 0.002 and shift is not None:
        A = T + (A - T).normalized() * (l1 + l2 - 0.002)
        p[cn].translation = pose[cn].translation + (A - pose[un].translation)
        dist = (T - A).length
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * max(dist, 1e-6))
    h = math.sqrt(max(0.0, l1 * l1 - along * along))
    src_dir_u = (pose[fn].translation - pose[un].translation).normalized()
    pole = src_dir_u - axis * src_dir_u.dot(axis)
    pole = pole.normalized() if pole.length > 1e-9 else Vector((0.0, 0.0, 1.0))
    if abs(delta) > 1e-9:
        pole = (pole * math.cos(delta) + axis.cross(pole) * math.sin(delta)).normalized()
    E = A + axis * along + pole * h
    src_dir_f = (T - pose[fn].translation).normalized()
    uq = src_dir_u.rotation_difference((E - A).normalized()) @ pose[un].to_quaternion()
    fq = src_dir_f.rotation_difference((T - E).normalized()) @ pose[fn].to_quaternion()
    for name, origin, q in ((un, A, uq), (fn, E, fq)):
        p[name] = Matrix.LocRotScale(origin, q, pose[name].to_scale())
        for suffix in ('01', '02'):
            twist = f"{'upperarm' if name == un else 'lowerarm'}_twist_{suffix}_{side}"
            if twist in p:
                p[twist] = p[name] @ pose[name].inverted() @ pose[twist]
    return p


def elbow_angle(pose, side):
    A = pose[f'upperarm_{side}'].translation
    E = pose[f'lowerarm_{side}'].translation
    T = pose[f'hand_{side}'].translation
    return math.degrees(math.acos(max(-1.0, min(1.0,
        (E - A).normalized().dot((T - E).normalized())))))


def beam(poses_in, side, frames, delta=0.0, shift=None):
    """Metrics of one candidate over the frames it can affect."""
    out = {f: solve_side(poses_in[f], side, delta, shift) for f in frames}
    eye = {f: eye_side(out[f], side) for f in frames}
    travel = max((out[f][f'lowerarm_{side}'].translation
                  - out[f - 1][f'lowerarm_{side}'].translation).length
                 for f in frames if f - 1 in out) * 100
    bend = [elbow_angle(out[f], side) for f in frames]
    ratio = max((poses_in[f][f'hand_{side}'].translation
                 - out[f][f'upperarm_{side}'].translation).length / REACH[side] for f in frames)
    return out, eye, travel, bend, ratio


blend_need = {s: [0.0] * (FRAMES + 1) for s in ('r', 'l')}
for s in ('r', 'l'):
    for f in range(FRAMES + 1):
        d = eye_side(poses[f], s, pts0[f])
        if d is None or d >= HI:
            continue
        blend_need[s][f] = 1.0 if d <= LO else (HI - d) / (HI - LO)
plan = {}
for s in ('r', 'l'):
    idx = [f for f in range(FRAMES + 1) if blend_need[s][f] > 0.01]
    if not idx:
        plan[s] = None
        continue
    lo, hi = min(idx), max(idx)
    win = list(range(max(0, lo - RAMP), min(FRAMES, hi + RAMP) + 1))
    base_worst = min((eye_side(poses[f], s, pts0[f]) or 1.0) for f in win)
    candidates = []
    for deg in range(0, 181, 10):
        for sign in ((1.0,) if deg == 0 else (1.0, -1.0)):
            candidates.append(('rotate', math.radians(deg) * sign, None))
    for d in DIRS:
        for m in MAGS:
            candidates.append(('shift', 0.0, Vector(d).normalized() * m))
    best = None
    board = []
    for kind, delta, shift in candidates:
        _, eye, travel, bend, ratio = beam(poses, s, win, delta, shift)
        worst = min((eye[f] if eye[f] is not None else 1.0) for f in win)
        sane = (ratio <= 0.96 and min(bend) >= 20.0 and max(bend) <= 175.0)
        ok = worst >= TARGET and sane
        # Among the candidates that clear the lens, prefer a plane rotation: it cannot
        # change the elbow angle or the reach at all (the elbow rides its own circle).
        # Then take the smallest correction, then the least elbow travel.
        amount = abs(math.degrees(delta)) if kind == 'rotate' else shift.length * 100
        score = ((1, 1 if kind == 'rotate' else 0, -amount, -travel) if ok
                 else (0, 0, worst, 0))
        row = dict(score=score, kind=kind, delta=delta, shift=shift, worst=worst, travel=travel,
                   ratio=ratio, bmin=min(bend), bmax=max(bend), ok=ok, amount=amount)
        board.append(row)
        if best is None or score > best['score']:
            best = row
    if 'debug' in ARGS:
        for row in sorted(board, key=lambda v: v['score'], reverse=True)[:12]:
            print('CAND', KEY, s, row['kind'],
                  round(math.degrees(row['delta']), 1) if row['kind'] == 'rotate'
                  else [round(v * 100, 1) for v in row['shift']],
                  'ok', row['score'][0], 'worst_cm', round(row['worst'] * 100, 1),
                  'travel_cm', round(row['travel'], 1), 'ratio', round(row['ratio'], 3),
                  'bend', [round(row['bmin'], 1), round(row['bmax'], 1)], flush=True)
    kind, delta, shift = best['kind'], best['delta'], best['shift']
    worst, travel, ratio, lo, hi = best['worst'], best['travel'], best['ratio'], min(idx), max(idx)
    # Ramp length follows the size of the correction, so a big plane swing cannot whip the
    # elbow: at most ~12 deg of swing, or ~4 cm of shoulder slide, per frame.
    ramp = max(RAMP, int(math.ceil(best['amount'] / 12.0)) if kind == 'rotate'
               else int(math.ceil(best['amount'] / 4.0)))
    ramp = min(ramp, 18)
    plan[s] = dict(kind=kind, delta=delta, shift=shift, lo=lo, hi=hi, worst_before=base_worst,
                   worst_after=worst, travel=travel, ratio=ratio, ramp=ramp,
                   bend=[round(best['bmin'], 1), round(best['bmax'], 1)])
    print('MELEE_FIX', KEY, s, 'kind', kind,
          'rotation_deg' if kind == 'rotate' else 'shift_cm',
          round(math.degrees(delta), 1) if kind == 'rotate' else [round(v * 100, 1) for v in shift],
          'window', [lo, hi], 'ramp', ramp, 'worst_before_cm', round(base_worst * 100, 1),
          'worst_after_cm', round(worst * 100, 1), 'elbow_travel_cm', round(travel, 1),
          'reach_ratio', round(ratio, 3), 'bend', plan[s]['bend'], flush=True)

fixed = [dict(p) for p in poses]
for f in range(FRAMES + 1):
    trial = poses[f]
    for s in ('r', 'l'):
        p = plan[s]
        if not p:
            continue
        R = p['ramp']
        w = 0.0
        if p['lo'] <= f <= p['hi']:
            w = 1.0
        elif f < p['lo']:
            k = p['lo'] - f
            if 0 < k <= R:
                x = 1.0 - k / R
                w = x ** 3 * (10 + x * (-15 + 6 * x))
        else:
            k = f - p['hi']
            if 0 < k <= R:
                x = 1.0 - k / R
                w = x ** 3 * (10 + x * (-15 + 6 * x))
        if w <= 1e-9:
            continue
        if p['kind'] == 'rotate':
            trial = solve_side(trial, s, delta=p['delta'] * w)
        else:
            trial = solve_side(trial, s, shift=p['shift'] * w)
    fixed[f] = trial

report = dict(key=KEY, source=str(BLEND), action=ACTION, target_cm=TARGET * 100, ramp=RAMP,
              game_tested=False)
for s in ('r', 'l'):
    src_eye = [eye_side(poses[f], s, pts0[f]) for f in range(FRAMES + 1)]
    new_eye = [eye_side(fixed[f], s) for f in range(FRAMES + 1)]
    per_frame = [round((fixed[f][f'lowerarm_{s}'].translation
                        - fixed[f - 1][f'lowerarm_{s}'].translation).length * 100, 2)
                 for f in range(1, FRAMES + 1)]
    src_travel = [round((poses[f][f'lowerarm_{s}'].translation
                         - poses[f - 1][f'lowerarm_{s}'].translation).length * 100, 2)
                  for f in range(1, FRAMES + 1)]
    report[s] = dict(
        plan=None if not plan[s] else {k: (list(v) if isinstance(v, Vector) else v)
                                       for k, v in plan[s].items()},
        eye_min_src_cm=round(min(v for v in src_eye if v is not None) * 100, 1),
        eye_min_new_cm=round(min(v for v in new_eye if v is not None) * 100, 1),
        frames_under15_src=[(f, round(src_eye[f] * 100, 1)) for f in range(FRAMES + 1)
                            if src_eye[f] is not None and src_eye[f] < 0.15],
        frames_under15_new=[(f, round(new_eye[f] * 100, 1)) for f in range(FRAMES + 1)
                            if new_eye[f] is not None and new_eye[f] < 0.15],
        elbow_src=[round(min(elbow_angle(poses[f], s) for f in range(FRAMES + 1)), 1),
                   round(max(elbow_angle(poses[f], s) for f in range(FRAMES + 1)), 1)],
        elbow_new=[round(min(elbow_angle(fixed[f], s) for f in range(FRAMES + 1)), 1),
                   round(max(elbow_angle(fixed[f], s) for f in range(FRAMES + 1)), 1)],
        elbow_travel_worst=sorted(((v, f + 1) for f, v in enumerate(per_frame)), reverse=True)[:4],
        elbow_travel_worst_src=sorted(((v, f + 1) for f, v in enumerate(src_travel)), reverse=True)[:4],
        eye_step_max_cm=round(max(abs((new_eye[f] or 1.0) - (new_eye[f - 1] or 1.0)) * 100
                                  for f in range(1, FRAMES + 1)), 2),
        eye_step_max_src_cm=round(max(abs((src_eye[f] or 1.0) - (src_eye[f - 1] or 1.0)) * 100
                                      for f in range(1, FRAMES + 1)), 2),
        reach_ratio_max=round(max((poses[f][f'hand_{s}'].translation
                                   - fixed[f][f'upperarm_{s}'].translation).length / REACH[s]
                                  for f in range(FRAMES + 1)), 3))
    print('MELEE_FIX', KEY, s, json.dumps({k: report[s][k] for k in
                                           ('eye_min_src_cm', 'eye_min_new_cm', 'elbow_src',
                                            'elbow_new', 'elbow_travel_worst',
                                            'elbow_travel_worst_src', 'eye_step_max_cm',
                                            'eye_step_max_src_cm', 'reach_ratio_max')}), flush=True)
report['hand_delta_mm'] = round(max(max((fixed[f][f'hand_{s}'].translation
                                         - poses[f][f'hand_{s}'].translation).length
                                        for s in ('r', 'l')) for f in range(FRAMES + 1)) * 1000, 5)
report['bone_delta_mm'] = round(max(abs((fixed[f][f'lowerarm_{s}'].translation
                                         - fixed[f][f'upperarm_{s}'].translation).length - LEN[f'{s}1'])
                                    + abs((fixed[f][f'hand_{s}'].translation
                                           - fixed[f][f'lowerarm_{s}'].translation).length - LEN[f'{s}2'])
                                    for f in range(FRAMES + 1) for s in ('r', 'l')) * 1000, 6)
report['gun_delta_mm'] = round(max((fixed[f]['WPN_root'].translation
                                    - poses[f]['WPN_root'].translation).length
                                   for f in range(FRAMES + 1)) * 1000, 5)
print('MELEE_FIX', KEY, 'invariants', json.dumps({k: report[k] for k in
                                                  ('hand_delta_mm', 'bone_delta_mm',
                                                   'gun_delta_mm')}), flush=True)

action = source.copy()
source.name = 'BASELINE_' + source.name
source.use_fake_user = True
action.name = ACTION
action.use_fake_user = True
curves = {(c.data_path, c.array_index): c
          for layer in action.layers for strip in layer.strips
          for bag in strip.channelbags for c in bag.fcurves}
for side in ('r', 'l'):
    for name in EDIT[side]:
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
                curve.keyframe_points.foreach_set('co', [v for f, row in enumerate(values)
                                                         for v in (f, row[j])])
                for k in curve.keyframe_points:
                    k.interpolation = 'LINEAR'
                curve.update()
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene = bpy.context.scene
scene.render.fps = FPS
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = 0, FRAMES
scene.frame_set(12)
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
report['out_blend'] = str(out_blend)
report['out_fbx'] = str(out_fbx)
(HERE / f'melee_fix_{KEY}.json').write_text(json.dumps(report, indent=2))
print('MELEE_FIX_WROTE', str(out_blend), str(out_fbx), flush=True)
