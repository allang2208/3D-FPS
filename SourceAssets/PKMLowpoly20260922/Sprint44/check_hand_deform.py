"""Does the forearm twist deform the HAND mesh?

Preserving hand_l's world matrix preserves the hand BONE, not the hand SURFACE: any
hand vertex that also carries weight on lowerarm_l / lowerarm_twist_01_l /
lowerarm_twist_02_l is dragged by the correction.  This measures that directly.

For every vertex whose weight is mostly on hand/finger bones, compare its skinned
position against where the hand bone's own rigid transform would put it.  A rigid
hand scores 0 at every frame regardless of the pose.
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

V7_BONES = list(E.V7_BONES)
WIDX, WVAL = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)['w_idx'], \
             np.load(E39 / 'v7_mesh.npz', allow_pickle=True)['w_val'].astype(np.float64)
V = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)['verts'].astype(np.float64)
HOMO = np.concatenate([V, np.ones((len(V), 1))], axis=1)

HAND_BONES = {n for n in V7_BONES
              if n == 'hand_l' or n.endswith('_l') and any(
                  n.startswith(p) for p in ('thumb_', 'index_', 'middle_', 'ring_',
                                            'pinky_'))}
RAMPED = set(E.RAMPED)
print('hand/finger bones: %d %s' % (len(HAND_BONES), sorted(HAND_BONES)[:6]))

W = np.zeros((len(V), len(V7_BONES)))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    a = (idx >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], idx[a]), w[a])

hand_idx = np.array([V7_BONES.index(n) for n in HAND_BONES])
ramp_idx = np.array([V7_BONES.index(n) for n in RAMPED])
share_hand = W[:, hand_idx].sum(axis=1)
share_ramp = W[:, ramp_idx].sum(axis=1)

HAND = np.where(share_hand > 0.5)[0]
print('vertices mostly on the hand: %d of %d' % (len(HAND), len(V)))
print('  of those, weight on the three ramped forearm bones:')
print('    mean %.4f  max %.4f  >1%%: %d  >5%%: %d  >20%%: %d'
      % (share_ramp[HAND].mean(), share_ramp[HAND].max(),
         int((share_ramp[HAND] > .01).sum()), int((share_ramp[HAND] > .05).sum()),
         int((share_ramp[HAND] > .20).sum())))
print('  weight distribution (share on hand bones): min %.3f  p1 %.3f'
      % (share_hand[HAND].min(), np.percentile(share_hand[HAND], 1)))

CASES = (('original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
          'PKM17_base_sprint_enter'),
         ('elbow41', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_enter_Elbow41.blend',
          'PKM_sprint_enter_Elbow41'),
         ('sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
          'PKM_sprint_enter_Sprint44'))

REPORT = {}
for tag, blend, action in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 120
    start, end = map(int, act.frame_range)
    rest_hand = np.array(E.AU_REST_M[E.AU_INDEX['hand_l']])
    pure = HAND[share_hand[HAND] > 0.98]
    print('  pure-hand vertices (>98%% on hand bones): %d, ramped weight max %.4f'
          % (len(pure), share_ramp[pure].max() if len(pure) else 0.0))
    per_frame = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
        rigid = pose['hand_l'] @ np.linalg.inv(rest_hand)
        skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in pose:
                skin[i] = pose[n] @ np.linalg.inv(
                    np.array(E.AU_REST_M[E.AU_INDEX[n]]))
        P = np.zeros((len(HAND), 3))
        hom = HOMO[HAND]
        for k in range(WIDX.shape[1]):
            idx, w = WIDX[HAND, k], WVAL[HAND, k]
            a = (idx >= 0) & (w > 0)
            P[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], hom[a])[:, :3]
        want = np.einsum('ij,nj->ni', rigid, HOMO[HAND])[:, :3]
        d = np.linalg.norm(P - want, axis=1) * 1000.0   # mm
        dp = np.linalg.norm(P[np.isin(HAND, pure)] - want[np.isin(HAND, pure)],
                            axis=1) * 1000.0 if len(pure) else np.array([0.0])
        if frame in (start, start + 16, end):
            order = np.argsort(-d)[:8]
            print('    worst vertices at f%d:' % frame)
            for o in order:
                gi = HAND[o]
                wl = [(V7_BONES[WIDX[gi, k]], round(float(WVAL[gi, k]), 3))
                      for k in range(WIDX.shape[1])
                      if WIDX[gi, k] >= 0 and WVAL[gi, k] > 0]
                print('      v%-6d %8.2f mm  t=%+.3f  %s' % (gi, d[o], 0.0, wl))
        per_frame.append({'frame': frame, 'mean_mm': float(d.mean()),
                          'max_mm': float(d.max()),
                          'pure_mean_mm': float(dp.mean()),
                          'pure_max_mm': float(dp.max())})
    worst = max(p['max_mm'] for p in per_frame)
    wmean = max(p['mean_mm'] for p in per_frame)
    jump = max(abs(b['mean_mm'] - a['mean_mm']) for a, b in zip(per_frame, per_frame[1:]))
    REPORT[tag] = {'worst_hand_deform_mm': round(worst, 3),
                   'worst_mean_mm': round(wmean, 3),
                   'max_per_frame_change_mm': round(jump, 3),
                   'frames': end - start + 1}
    print('\n%-9s hand deformation vs its own rigid bone (mm):' % tag)
    print('   worst vertex %.3f   worst frame mean %.3f   max frame-to-frame %.3f'
          % (worst, wmean, jump))
    pm = max(p['pure_max_mm'] for p in per_frame)
    print('   pure-hand worst %.3f mm   mean %.3f mm' % (pm, max(p['pure_mean_mm'] for p in per_frame)))
    for p in per_frame[::8] + [per_frame[-1]]:
        print('     f%-4d mean %7.3f  max %7.3f' % (p['frame'], p['mean_mm'], p['max_mm']))

(ROOT / 'Sprint44' / 'hand_deform.json').write_text(
    json.dumps(REPORT, indent=2), encoding='utf-8')
print('\nHAND_DEFORM_DONE')