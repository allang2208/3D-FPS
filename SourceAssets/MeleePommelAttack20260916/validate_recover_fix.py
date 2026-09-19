"""Final validation of the elbow-plane release window before re-baking.

Reports, for the shortlisted candidates and the current 12-frame baseline:

  tail curve    per-frame armature AND parent-relative joint deltas over the
                last 0.22 s, so the "decelerate, then re-accelerate, then stop"
                shape of the baseline is visible next to the fixed versions.
  entry curve   same over the first 0.22 s.
  baseline      a run with the separation disabled (release window = 1), i.e.
                the authored pose path alone, so any residual motion at the last
                frame can be attributed to the pose path rather than the fix.
  endpoints     the first/last frame armature poses against the authored idle
                (must match) and the correction magnitude at both endpoints
                (must be exactly 0).
  quality       forearm crossings and narrowest elbow gap.

Read-only w.r.t. assets: solves and prints.
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parent
OUT = P / 'recover_fix_validation.json'
sys.path.insert(0, str(P))

from arm_solver import (ArmSolver, forearms_cross_in_view, segment_gap)   # noqa: E402
from pommel_motion import *                                              # noqa: E402

# ---- setup (identical to author_pommel_strike.py) --------------------------
donor = ROOT / 'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
bpy.context.scene.frame_set(0)
r = bpy.data.objects['SK_M4_Infima']
rest_m4 = {b.name: b.matrix_local.copy() for b in r.data.bones}
pose_m4 = {b.name: b.matrix.copy() for b in r.pose.bones}
fit = json.loads((ROOT / 'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G = pose_m4['WPN_root'] @ Matrix(fit['grip_in_root'])
S = Matrix.Diagonal((-1, 1, 1, 1))
GR = S @ G @ S
leftnames = [b.name for b in r.pose.bones
             if b.name.endswith('_l') and any(b.name.startswith(x) for x in
                                              ['index', 'middle', 'ring', 'pinky', 'thumb'])]
left_rel = {n: pose_m4['hand_l'].inverted() @ pose_m4[n] for n in leftnames}
mirrored = {n[:-1] + 'r': S @ (pose_m4[n] @ rest_m4[n].inverted()) @ S @ rest_m4[n[:-1] + 'r']
            for n in ['hand_l'] + leftnames}
right_rel = {n: mirrored['hand_r'].inverted() @ m for n, m in mirrored.items() if n != 'hand_r'}
HL = Matrix.Translation((0, 0, .06)) @ G.inverted() @ pose_m4['hand_l']
HR = Matrix.Translation((0, 0, .06)) @ GR.inverted() @ mirrored['hand_r']
for grasp in [HL, HR]:
    radial = Vector((grasp.translation.x, grasp.translation.y, 0))
    if radial.length > .0025:
        grasp.translation -= radial.normalized() * .0025

source = ROOT / 'RuneSword20260913/ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
r = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
solver = ArmSolver(rest, {'l': HL, 'r': HR}, {'l': left_rel, 'r': right_rel})
solver.ready_pose(READY)
s.render.fps = FPS
s.render.fps_base = 1

paired = [poses(f / FPS) for f in range(round(ATTACK_END * FPS) + 1)]
frames = [p[0] for p in paired]
hold = (math.ceil(RAISE_END * FPS), math.floor(CONTACT_START * FPS))

print('SOLVING_GRASP', flush=True)
grasps = solver.fit_path(frames, False, hold)
print('SOLVING_SUPPORT', flush=True)
supports = solver.fit_support(frames, grasps, hold)
n = len(frames)
hands = {side: [solver.hand(side, frames[f], grasps[side][f]) for f in range(n)] for side in ('l', 'r')}

BONES = ('upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_r', 'lowerarm_r', 'hand_r')


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


def bake(chains_now):
    """Returns armature quats and parent-relative quat deltas per frame."""
    out = []
    prev_local = {}
    for f in range(n):
        p = {name: m.copy() for name, m in rest.items()}
        for side in ('l', 'r'):
            solver.apply_arm(p, side, solver.hand(side, frames[f], grasps[side][f]), chains_now[side][f])
        row = {b: p[b].to_quaternion().copy() for b in BONES}
        for side in ('l', 'r'):
            for child, parent in (('lowerarm_' + side, 'upperarm_' + side),
                                  ('hand_' + side, 'lowerarm_' + side)):
                row['local_' + child] = p[child].to_quaternion().rotation_difference(p[parent].to_quaternion())
        out.append(row)
    return out


def run(label, win_in, win_out, taps, separate=True):
    os.environ['ARM_RELEASE_IN'] = str(win_in)
    os.environ['ARM_RELEASE_OUT'] = str(win_out)
    os.environ['ARM_PATH_TAPS'] = str(taps)
    print('== %s in=%s out=%s taps=%s separate=%s' % (label, win_in, win_out, taps, separate), flush=True)
    if separate:
        chains = solver.separate_arms(frames, grasps, {side: list(supports[side]) for side in ('l', 'r')}, hold)
    else:
        chains = {side: list(supports[side]) for side in ('l', 'r')}
    arm = bake(chains)

    mag = {side: [(Vector(chains[side][f][1]) - Vector(supports[side][f][1])).length * 100 for f in range(n)]
           for side in ('l', 'r')}
    i_tail = n - 1 - int(0.22 * FPS)
    i_entry = int(0.22 * FPS)

    crossings = 0
    min_gap = 9e9
    for f in range(n):
        Al, El = chains['l'][f]
        Ar, Er = chains['r'][f]
        if forearms_cross_in_view(El, hands['l'][f].translation, Er, hands['r'][f].translation):
            crossings += 1
        min_gap = min(min_gap, segment_gap(Al, El, Ar, Er))

    res = {'label': label, 'in': win_in, 'out': win_out, 'taps': taps, 'separate': separate,
           'crossings': crossings, 'min_gap_cm': round(min_gap * 100, 2),
           'mag_first_cm': round(mag['l'][0], 5), 'mag_last_cm': round(mag['l'][-1], 5),
           'mag_max_cm': round(max(max(mag['l']), max(mag['r'])), 3),
           'arm_tail': {}, 'local_tail': {}, 'arm_entry': {}, 'local_entry': {}}
    keys = list(arm[0].keys())
    for b in keys:
        ws = [delta_deg(arm[f - 1][b], arm[f][b]) for f in range(1, n)]
        res['arm_tail'][b] = [round(v, 3) for v in ws[i_tail:]]
        res['arm_entry'][b] = [round(v, 3) for v in ws[:i_entry]]
    res['summary'] = {
        'tail_max': round(max(max(res['arm_tail'][b]) for b in keys), 3),
        'tail_last': round(max(res['arm_tail'][b][-1] for b in keys), 3),
        'entry_max': round(max(max(res['arm_entry'][b]) for b in keys), 3),
        'whole_max': None,
    }
    # whole-clip maxima for context
    whole = {}
    for b in keys:
        ws = [delta_deg(arm[f - 1][b], arm[f][b]) for f in range(1, n)]
        whole[b] = round(max(ws), 3)
    res['summary']['whole_max'] = max(whole.values())
    res['whole_per_bone'] = whole
    # endpoints: first / last frame armature quats for the report
    res['endpoint_pose'] = {b: [list(map(lambda v: round(v, 6), arm[0][b])),
                                list(map(lambda v: round(v, 6), arm[-1][b]))] for b in BONES}
    return res


results = []
results.append(run('pose_only', 1, 1, 5, separate=False))
for label, win_in, win_out, taps, mw in (
        ('baseline_12', 12, 12, 5, 100),
        ('release_48', 48, 48, 9, 100),
        ('release_144', 144, 144, 9, 100),
        ('w48_m300', 48, 48, 9, 300),
        ('w48_m1000', 48, 48, 9, 1000),
        ('w240_m300', 240, 240, 9, 300),
        ('w240_m1000', 240, 240, 9, 1000)):
    os.environ['ARM_MOVEMENT_WEIGHT'] = str(mw)
    res = run(label, win_in, win_out, taps)
    res['movement_weight'] = mw
    results.append(res)

OUT.write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')
print('label           tail_max  tail_last  entry_max  whole_max  crossings  min_gap  mag_first  mag_last')
for res in results:
    print('%-15s %8.3f  %9.3f  %9.3f  %9.3f  %9d  %7.2f  %9.5f  %8.5f'
          % (res['label'], res['summary']['tail_max'], res['summary']['tail_last'],
             res['summary']['entry_max'], res['summary']['whole_max'],
             res['crossings'], res['min_gap_cm'], res['mag_first_cm'], res['mag_last_cm']), flush=True)
print('WROTE', OUT)