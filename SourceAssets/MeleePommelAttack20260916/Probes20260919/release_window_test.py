"""Pick the elbow-plane release window by measuring the arms' per-frame deltas.

Solves the pommel path once, then re-runs only `separate_arms` for each candidate
release window (in/out frames), measuring what the player sees at both clip ends:

  tail    last 0.15 s: max per-frame armature-space rotation delta of
          upperarm/lowerarm/hand on both sides, and the delta on the final frame.
          The baseline defect shows up here as a re-acceleration burst
          (~2.0 deg/frame = ~950 deg/s) after the arms had already slowed to
          ~0.1 deg/frame.
  entry   first 0.15 s: the mirror ramp-in.
  |E1-E0| elbow-plane correction magnitude: max over the clip plus the values at
          the first and last frames. It must be exactly 0 at both endpoints
          (that is what matches the accepted idle), and wherever it collapses it
          must do so under the surrounding motion, not on its own.

Read-only w.r.t. assets: solves and prints. No export, no save.
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
OUT = P / 'release_window_test.json'
sys.path.insert(0, str(P))

import arm_solver                        # noqa: E402
from arm_solver import ArmSolver         # noqa: E402
from pommel_motion import *              # noqa: E402

# ---- same setup as author_pommel_strike.py ---------------------------------
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


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


def bake_armature(grasps_side, chains_side):
    """Armature-space quaternions per bone plus parent-relative joint deltas.

    The parent-relative numbers are what the eye reads as a joint pop: the world
    hand pose is set from the grasp frame, so when the elbow plane collapses the
    wrist absorbs the difference and only the local decomposition shows it.
    """
    out = []
    for f in range(n):
        p = {name: m.copy() for name, m in rest.items()}
        solver.apply_arm(p, 'l', solver.hand('l', frames[f], grasps_side['l'][f]), chains_side['l'][f])
        solver.apply_arm(p, 'r', solver.hand('r', frames[f], grasps_side['r'][f]), chains_side['r'][f])
        row = {b: p[b].to_quaternion().copy() for b in
               ('upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_r', 'lowerarm_r', 'hand_r')}
        for side in ('l', 'r'):
            for child, parent in (('lowerarm_' + side, 'upperarm_' + side),
                                  ('hand_' + side, 'lowerarm_' + side)):
                row['local_' + child] = p[child].to_quaternion().rotation_difference(p[parent].to_quaternion())
        out.append(row)
    return out


def measure(win_in, win_out):
    os.environ['ARM_RELEASE_IN'] = str(win_in)
    os.environ['ARM_RELEASE_OUT'] = str(win_out)
    print('-- separate_arms in=%d out=%d' % (win_in, win_out), flush=True)
    chains = solver.separate_arms(frames, grasps, {side: list(supports[side]) for side in ('l', 'r')}, hold)
    mag_l = [(Vector(chains['l'][f][1]) - Vector(supports['l'][f][1])).length * 100 for f in range(n)]
    mag_r = [(Vector(chains['r'][f][1]) - Vector(supports['r'][f][1])).length * 100 for f in range(n)]
    arm = bake_armature(grasps, chains)
    tail0 = n - 1 - int(0.15 * FPS)
    entry1 = int(0.15 * FPS)
    keys = [k for k in arm[0] if k != 'local']
    res = {'in': win_in, 'out': win_out,
           'mag_max_cm': round(max(max(mag_l), max(mag_r)), 3),
           'mag_first_cm': round(mag_l[0], 4), 'mag_last_cm': round(mag_l[-1], 4),
           'mag_at_entry6': round(mag_l[6], 3), 'mag_at_tail12': round(mag_l[n - 13], 3),
           'tail': {}, 'entry': {}, 'tail_curve': {}, 'after_strike': {}, 'whole': {}}
    # windows over time: entry <=0.35 s, after the strike (arrest ends 0.98 s) >1.05 s
    i_entry = int(0.35 * FPS)
    i_after = int(1.05 * FPS)
    for b in keys:
        ws = [delta_deg(arm[f - 1][b], arm[f][b]) for f in range(1, n)]
        tail = ws[tail0:]
        entry = ws[:entry1]
        after = ws[i_after:]
        res['tail'][b] = {'max': round(max(tail), 3), 'last': round(tail[-1], 3)}
        res['entry'][b] = {'max': round(max(entry), 3), 'first': round(entry[0], 3)}
        res['after_strike'][b] = {'max': round(max(after), 3), 'at': int(i_after + after.index(max(after)) + 1)}
        res['whole'][b] = {'max': round(max(ws), 3)}
        if b in ('upperarm_r', 'upperarm_l', 'local_lowerarm_r', 'local_hand_r', 'lowerarm_r'):
            res['tail_curve'][b] = [round(ws[f], 3) for f in range(n - 96, n - 1)]
    res['mag_r_curve'] = [round(m * 100, 2) for m in mag_r[:6]] + ['...'] + \
                         [round(m * 100, 2) for m in mag_r[6:n - 12:60]] + \
                         [round(m * 100, 2) for m in mag_r[-6:]]
    # correction strength where the strike and the withdraw need it
    strike = [mag_r[f] for f in range(int(CONTACT_START * FPS), int(ARREST_END * FPS))]
    withdraw = [mag_r[f] for f in range(int(ARREST_END * FPS), int(RETURN_CORNER * FPS))]
    res['mag_strike_mean_cm'] = round(sum(strike) / len(strike), 3)
    res['mag_strike_min_cm'] = round(min(strike), 3)
    res['mag_withdraw_mean_cm'] = round(sum(withdraw) / len(withdraw), 3)
    return res


CANDIDATES = [(12, 12, 5), (48, 48, 5), (48, 48, 15), (72, 72, 5), (72, 72, 15),
              (48, 240, 5), (48, 240, 9), (240, 240, 9), (144, 144, 9)]
results = []
for win_in, win_out, taps in CANDIDATES:
    os.environ['ARM_PATH_TAPS'] = str(taps)
    res = measure(win_in, win_out)
    res['taps'] = taps
    results.append(res)

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
print('WINDOW  tail_max tail_last entry_max whole_max after_max@f  mag_max loc_tail loc_entry  (correction cm)')
for res in results:
    limb = ('upperarm', 'lowerarm', 'hand')
    tail_max = max(v['max'] for k, v in res['tail'].items() if k.startswith(limb))
    tail_last = max(v['last'] for k, v in res['tail'].items() if k.startswith(limb))
    entry_max = max(v['max'] for k, v in res['entry'].items() if k.startswith(limb))
    whole_max = max(v['max'] for k, v in res['whole'].items() if k.startswith(limb))
    after = max((v for k, v in res['after_strike'].items() if k.startswith(limb)), key=lambda v: v['max'])
    loc_tail = max((v['max'] for k, v in res['tail'].items() if k.startswith('local_')), default=0)
    loc_entry = max((v['max'] for k, v in res['entry'].items() if k.startswith('local_')), default=0)
    print('%3d/%-3d taps=%2d  %7.3f  %7.3f  %8.3f  %8.3f  %8.3f@%4d  %7.2f  %6.3f  %6.3f  strike %5.2f/%5.2f withdraw %5.2f'
          % (res['in'], res['out'], res['taps'], tail_max, tail_last, entry_max, whole_max,
             after['max'], after['at'], res['mag_max_cm'], loc_tail, loc_entry,
             res['mag_strike_mean_cm'], res['mag_strike_min_cm'], res['mag_withdraw_mean_cm']), flush=True)
print('WROTE', OUT)