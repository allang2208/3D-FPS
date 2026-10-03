"""Is the hand's skinning unusually distorted during the sprint, or is it the base?

Standard measure: for each vertex, the blended matrix B = sum w_b * skin_b should be
a rigid transform.  ||B3'B3 - I||_F is how far it is from rigid - candy-wrapper and
joint collapse show up here.  Compare the sprint entry against the accepted idle,
which uses the same mesh and the same hand bones.
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)

md = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
V7_BONES = list(md['bones'])
WIDX, WVAL = md['w_idx'], md['w_val'].astype(np.float64)
AU_INDEX = E.AU_INDEX
HAND_BONES = {n for n in V7_BONES if n == 'hand_l' or (
    n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')))}
FORE_BONES = {'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'}
hidx = [V7_BONES.index(n) for n in HAND_BONES]
W = np.zeros((len(V7_BONES) and len(md['verts']), len(V7_BONES)))
for k in range(WIDX.shape[1]):
    i2, w = WIDX[:, k], WVAL[:, k]
    a = (i2 >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], i2[a]), w[a])
share_hand = W[:, hidx].sum(axis=1)
HAND = np.where(share_hand > 0.5)[0]
FORE_IN_HAND = np.where((share_hand > 0.5)
                        & (W[:, [V7_BONES.index(n) for n in FORE_BONES]].sum(axis=1) > 0.01))[0]
print('hand verts %d ; of those with >1%% forearm weight: %d' % (len(HAND), len(FORE_IN_HAND)))

CASES = (
    ('idle (accepted baseline)', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
     'PKM_Game_idle', 60),
    ('sprint_enter original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_enter', 120),
    ('sprint_enter sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
     'PKM_sprint_enter_Sprint44', 120),
    ('sprint_loop sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_loop_Sprint44.blend',
     'PKM_sprint_loop_Sprint44', 120),
)

out = {}
for tag, blend, action, fps in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = fps
    start, end = map(int, act.frame_range)
    rows = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
        skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in pose:
                skin[i] = pose[n] @ np.linalg.inv(np.array(E.AU_REST_M[AU_INDEX[n]]))
        B = np.zeros((len(HAND), 3, 3))
        for k in range(WIDX.shape[1]):
            idx, w = WIDX[HAND, k], WVAL[HAND, k]
            a = (idx >= 0) & (w > 0)
            B[a] += w[a, None, None] * skin[idx[a]][:, :3, :3]
        M = np.einsum('nji,njk->nik', B, B) - np.eye(3)
        err = np.linalg.norm(M, axis=(1, 2))
        rows.append({'frame': frame, 'mean': float(err.mean()), 'max': float(err.max()),
                     'p99': float(np.percentile(err, 99))})
    worst = max(rows, key=lambda r: r['max'])
    out[tag] = {'frames': end - start + 1,
                'worst_max': round(worst['max'], 4), 'at_frame': worst['frame'],
                'worst_mean': round(max(r['mean'] for r in rows), 4),
                'worst_p99': round(max(r['p99'] for r in rows), 4)}
    print('  %-26s worst |B\'B-I| max %.4f (f%d)  mean %.4f  p99 %.4f'
          % (tag, worst['max'], worst['frame'],
             out[tag]['worst_mean'], out[tag]['worst_p99']))

(ROOT / 'Sprint44' / 'hand_skin.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('HAND_SKIN_DONE')