"""Trace the full-clip channel profile so every pulse is attributed to a channel.

Prints, for the left and right arm, per-frame deltas of the three authoring
channels the arm is built from:
    grasp angle  -- the hand's angle around the hilt (fit_path)
    shoulder A   -- shoulder anchor (fit_support / separate_arms)
    elbow E      -- solved elbow position (fit_support, then separate_arms)
plus the armature-space rotation deltas of upperarm / lowerarm / hand, so a
pulse in a bone can be read against the channel that produced it.

Read-only.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parent
OUT = P / 'channel_profile.json'
sys.path.insert(0, str(P))

from arm_solver import ArmSolver          # noqa: E402
from pommel_motion import *               # noqa: E402

# ---- same setup as author_pommel_strike.py ---------------------------------
donor = ROOT / 'MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
bpy.context.scene.frame_set(0)
r = bpy.data.objects['SK_M4_Infima']
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
pose = {b.name: b.matrix.copy() for b in r.pose.bones}
fit = json.loads((ROOT / 'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text())
G = pose['WPN_root'] @ Matrix(fit['grip_in_root'])
S = Matrix.Diagonal((-1, 1, 1, 1))
GR = S @ G @ S
leftnames = [b.name for b in r.pose.bones
             if b.name.endswith('_l') and any(b.name.startswith(x) for x in
                                              ['index', 'middle', 'ring', 'pinky', 'thumb'])]
left_rel = {n: pose['hand_l'].inverted() @ pose[n] for n in leftnames}
mirrored = {n[:-1] + 'r': S @ (pose[n] @ rest[n].inverted()) @ S @ rest[n[:-1] + 'r']
            for n in ['hand_l'] + leftnames}
right_rel = {n: mirrored['hand_r'].inverted() @ m for n, m in mirrored.items() if n != 'hand_r'}
HL = Matrix.Translation((0, 0, .06)) @ G.inverted() @ pose['hand_l']
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

print('SOLVING', flush=True)
grasps = solver.fit_path(frames, False, hold)
supports = solver.fit_support(frames, grasps, hold)
chains = solver.separate_arms(frames, grasps, {side: list(supports[side]) for side in ('l', 'r')}, hold)

n = len(frames)
rows = []
for f in range(n):
    row = {'f': f, 't': round(f / FPS, 4)}
    for side in ('l', 'r'):
        A0, E0 = supports[side][f]
        A1, E1 = chains[side][f]
        row['grasp_' + side] = round(math.degrees(grasps[side][f]), 3)
        row['A0_' + side] = [round(v, 5) for v in A0]
        row['E0_' + side] = [round(v, 5) for v in E0]
        row['A1_' + side] = [round(v, 5) for v in A1]
        row['E1_' + side] = [round(v, 5) for v in E1]
    rows.append(row)


def dist_row(a, b, k):
    return (Vector(b[k + '_l']) - Vector(a[k + '_l'])).length * 100, \
           (Vector(b[k + '_r']) - Vector(a[k + '_r'])).length * 100


deltas = []
for i in range(1, n):
    a, b = rows[i - 1], rows[i]
    dd = {'f': b['f'], 't': b['t'],
          'dgrasp_l': round(abs(b['grasp_l'] - a['grasp_l']), 4),
          'dgrasp_r': round(abs(b['grasp_r'] - a['grasp_r']), 4)}
    for k in ('A0', 'E0', 'A1', 'E1'):
        dl, dr = dist_row(a, b, k)
        dd['d' + k + '_l'] = round(dl, 4)
        dd['d' + k + '_r'] = round(dr, 4)
    deltas.append(dd)

# report the largest channel jumps anywhere in the clip
head = ['dgrasp_l', 'dgrasp_r', 'dE1_l', 'dE1_r', 'dA1_l', 'dA1_r']
summary = {}
for k in head:
    mx = max(deltas, key=lambda x: x[k])
    summary[k] = {'value': mx[k], 'f': mx['f'], 't': mx['t']}

OUT.write_text(json.dumps({'deltas': deltas, 'summary': summary}, ensure_ascii=False), encoding='utf-8')
print('CHANNEL_SUMMARY', json.dumps(summary, ensure_ascii=False), flush=True)
print('WROTE', OUT)