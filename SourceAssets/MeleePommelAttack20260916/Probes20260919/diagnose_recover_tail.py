"""Locate the late re-acceleration pulse in the pommel clip's recover tail.

The UE-side measurement (480 Hz, armature space) shows the right upper arm and
forearm decelerating to ~0 deg/frame around 1.55 s, then re-accelerating to
~2 deg/frame (~950 deg/s) at 1.575-1.59 s, and the clip ending while the arm is
still moving ~100 deg/s. That pulse is already in the authored bake, so it has
to be traced through the solving chain before it is fixed:

    grasps      fit_path        grasp angle around the hilt per side
    supports    fit_support     shoulder anchor A + elbow pole angle
    chains      separate_arms   elbow-plane offset per side

Prints the last 120 frames of each channel (per-frame deltas) so the channel
that produces the pulse is named, not guessed. Read-only: opens the sources,
solves, prints. No export, no save.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

P = Path(__file__).parent
ROOT = P.parent
OUT = P / 'recover_tail_probe.json'
sys.path.insert(0, str(P))

from arm_solver import ArmSolver          # noqa: E402
from pommel_motion import *               # noqa: E402

TAIL = 120                                # frames printed (~0.25 s at 480 Hz)

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
localrest = {n: (rest[r.data.bones[n].parent.name].inverted() @ m if r.data.bones[n].parent else m)
             for n, m in rest.items()}
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
print('SOLVING_SEPARATE', flush=True)
chains_before = {side: list(supports[side]) for side in ('l', 'r')}
chains = solver.separate_arms(frames, grasps, {side: list(supports[side]) for side in ('l', 'r')}, hold)

n = len(frames)
tail = list(range(max(0, n - TAIL), n))


def d(a, b):
    return math.degrees(abs(a - b))


rows = []
for f in tail:
    row = {'f': f, 't': round(f / FPS, 4)}
    for side in ('l', 'r'):
        row['grasp_' + side] = round(math.degrees(grasps[side][f]), 3)
        A0, E0 = supports[side][f]
        A1, E1 = chains[side][f]
        row['A0_' + side] = [round(v, 4) for v in A0]
        row['E0_' + side] = [round(v, 4) for v in E0]
        row['A1_' + side] = [round(v, 4) for v in A1]
        row['E1_' + side] = [round(v, 4) for v in E1]
        # elbow-plane angle of the corrected chain (same convention as fit_support)
        axis = (Vector(E1) - Vector(A1)).normalized()
        down = Vector((-.45 if side == 'l' else .45, -.15, -1))
        down -= axis * down.dot(axis)
        down.normalize()
        lateral = axis.cross(down)
        pole = Vector(E1) - (Vector(A1) + axis * (Vector(E1) - Vector(A1)).dot(axis))
        row['plane_' + side] = round(math.degrees(math.atan2(pole.dot(lateral), pole.dot(down))), 3)
        row['axis_' + side] = [round(v, 4) for v in axis]
    rows.append(row)

# per-frame deltas of the channels that can move the arm: grasp angle, pole plane,
# shoulder anchor, and elbow position
deltas = []
for i in range(1, len(rows)):
    a, b = rows[i - 1], rows[i]
    dd = {'f': b['f'], 't': b['t']}
    for side in ('l', 'r'):
        dd['dgrasp_' + side] = round(d(b['grasp_' + side], a['grasp_' + side]), 4)
        dd['dplane_' + side] = round(d(b['plane_' + side], a['plane_' + side]), 4)
        dd['dA1_' + side] = round((Vector(b['A1_' + side]) - Vector(a['A1_' + side])).length, 4)
        dd['dE1_' + side] = round((Vector(b['E1_' + side]) - Vector(a['E1_' + side])).length, 4)
        dd['dE0_' + side] = round((Vector(b['E0_' + side]) - Vector(a['E0_' + side])).length, 4)
    deltas.append(dd)

peak = {}
for key in ('dgrasp_l', 'dgrasp_r', 'dplane_l', 'dplane_r', 'dA1_l', 'dA1_r', 'dE1_l', 'dE1_r'):
    mx = max(deltas, key=lambda x: x[key])
    peak[key] = {'value': mx[key], 'f': mx['f'], 't': mx['t']}

OUT.write_text(json.dumps({'rows': rows, 'deltas': deltas, 'peaks': peak},
                          ensure_ascii=False, indent=1), encoding='utf-8')
print('RECOVER_TAIL_PROBE', json.dumps(peak, ensure_ascii=False), flush=True)
print('WROTE', OUT, flush=True)