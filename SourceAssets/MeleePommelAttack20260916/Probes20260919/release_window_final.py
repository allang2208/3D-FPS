"""Choose the elbow-plane release window: final measurement pass.

Solves the pommel path once, then re-runs `separate_arms` per candidate release
window and reports what the player would see:

  tail curve   per-frame armature-space deltas over the last 0.20 s, all six arm
               bones. The shipped clip re-accelerates to ~2.0 deg/frame
               (~950 deg/s) at 1.587 s after having slowed to ~0.1 deg/frame,
               i.e. a late twitch right before the hand-back to idle.
  entry curve  first 0.20 s, the mirror ramp-in.
  quality      forearm crossings in view and the narrowest elbow-to-elbow
               segment gap, so a window that throws away the separation is
               rejected instead of only making the tail quiet.

Read-only w.r.t. assets.
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
OUT = P / 'release_window_final.json'
sys.path.insert(0, str(P))

from arm_solver import (ArmSolver, forearms_cross_in_view, segment_gap)   # noqa: E402
from pommel_motion import *                                              # noqa: E402

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
hands = {side: [solver.hand(side, frames[f], grasps[side][f]) for f in range(n)] for side in ('l', 'r')}

BONES = ('upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_r', 'lowerarm_r', 'hand_r')


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


def bake(grasps_now, chains_now):
    out = []
    for f in range(n):
        p = {name: m.copy() for name, m in rest.items()}
        for side in ('l', 'r'):
            solver.apply_arm(p, side, solver.hand(side, frames[f], grasps_now[side][f]), chains_now[side][f])
        out.append({b: p[b].to_quaternion().copy() for b in BONES})
    return out


def measure(win_in, win_out, taps):
    os.environ['ARM_RELEASE_IN'] = str(win_in)
    os.environ['ARM_RELEASE_OUT'] = str(win_out)
    os.environ['ARM_PATH_TAPS'] = str(taps)
    print('-- separate_arms in=%d out=%d taps=%d' % (win_in, win_out, taps), flush=True)
    chains = solver.separate_arms(frames, grasps, {side: list(supports[side]) for side in ('l', 'r')}, hold)
    arm = bake(grasps, chains)
    i_tail = n - 1 - int(0.20 * FPS)
    i_entry = int(0.20 * FPS)

    crossings = 0
    min_gap = 9e9
    for f in range(n):
        Al, El = chains['l'][f]
        Ar, Er = chains['r'][f]
        Tl = hands['l'][f].translation
        Tr = hands['r'][f].translation
        if forearms_cross_in_view(El, Tl, Er, Tr):
            crossings += 1
        min_gap = min(min_gap, segment_gap(Al, El, Ar, Er))

    res = {'in': win_in, 'out': win_out, 'taps': taps,
           'crossings': crossings, 'min_gap_cm': round(min_gap * 100, 2),
           'tail_curve': {}, 'entry_curve': {}, 'summary': {}}
    for b in BONES:
        ws = [delta_deg(arm[f - 1][b], arm[f][b]) for f in range(1, n)]
        res['tail_curve'][b] = [round(v, 3) for v in ws[i_tail:]]
        res['entry_curve'][b] = [round(v, 3) for v in ws[:i_entry]]
        res['summary'][b] = {
            'tail_max': round(max(ws[i_tail:]), 3),
            'tail_last': round(ws[-1], 3),
            'entry_max': round(max(ws[:i_entry]), 3),
            'whole_max': round(max(ws), 3),
        }
    return res


CANDIDATES = [(12, 12, 5), (48, 48, 5), (48, 48, 9), (144, 144, 9), (192, 144, 9), (240, 240, 9)]
results = []
for win_in, win_out, taps in CANDIDATES:
    results.append(measure(win_in, win_out, taps))

OUT.write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')
print('window  taps  tail_max  tail_last  entry_max  whole_max  crossings  min_gap_cm')
for res in results:
    print('%3d/%-3d %2d  %8.3f  %8.3f  %9.3f  %9.3f  %9d  %9.2f'
          % (res['in'], res['out'], res['taps'],
             max(v['tail_max'] for v in res['summary'].values()),
             max(v['tail_last'] for v in res['summary'].values()),
             max(v['entry_max'] for v in res['summary'].values()),
             max(v['whole_max'] for v in res['summary'].values()),
             res['crossings'], res['min_gap_cm']), flush=True)
print('WROTE', OUT)