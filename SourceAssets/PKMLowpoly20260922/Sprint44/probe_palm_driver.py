"""What drives the palm collapse at f3-f5?

For a palm vertex the blended matrix B = sum w_b * skin_b is non-rigid in proportion
to how differently the blended bones are ORIENTED.  So print, per frame, the relative
rotation angle between hand_l and each forearm bone it shares palm weight with, next
to the palm collapse, and see which pair tracks it.
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
W = np.zeros((len(md['verts']), len(V7_BONES)))
for k in range(WIDX.shape[1]):
    i2, w = WIDX[:, k], WVAL[:, k]
    a = (i2 >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], i2[a]), w[a])
FORE = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l']
PALM = {n for n in V7_BONES if n == 'hand_l' or n.endswith('_metacarpal_l')}
FINGER = {n for n in V7_BONES if n.endswith('_l') and n.startswith(
    ('thumb_0', 'index_0', 'middle_0', 'ring_0', 'pinky_0'))}
pi = [V7_BONES.index(n) for n in PALM]
fi = [V7_BONES.index(n) for n in FINGER]
psh, fsh = W[:, pi].sum(axis=1), W[:, fi].sum(axis=1)
PALMV = np.where((psh > 0.6) & (fsh < 0.2))[0]

# what share of the palm actually rides on each forearm bone
print('palm vertices: %d' % len(PALMV))
for n in FORE:
    s = W[PALMV, V7_BONES.index(n)]
    print('   weight on %-22s mean %.4f  max %.4f  >5%%: %d'
          % (n, s.mean(), s.max(), int((s > .05).sum())))

CASES = (('original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
          'PKM17_base_sprint_enter'),
         ('sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
          'PKM_sprint_enter_Sprint44'))

for tag, blend, action in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 120
    start, end = map(int, act.frame_range)
    print('\n%s — per frame f0..f10' % tag)
    print('  frame   collapse   rel(hand,lowerarm)  rel(hand,tw02)  rel(hand,tw01)   '
          'd(collapse)')
    prev = None
    for frame in range(start, min(start + 11, end + 1)):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
        skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in pose:
                skin[i] = pose[n] @ np.linalg.inv(np.array(E.AU_REST_M[AU_INDEX[n]]))
        B = np.zeros((len(PALMV), 3, 3))
        for k in range(WIDX.shape[1]):
            idx, w = WIDX[PALMV, k], WVAL[PALMV, k]
            a = (idx >= 0) & (w > 0)
            B[a] += w[a, None, None] * skin[idx[a]][:, :3, :3]
        M = np.einsum('nji,njk->nik', B, B) - np.eye(3)
        e = np.linalg.norm(M, axis=(1, 2))
        p99 = float(np.percentile(e, 99))

        def rel(a, b):
            Ra = skin[V7_BONES.index(a)][:3, :3]
            Rb = skin[V7_BONES.index(b)][:3, :3]
            # rigid part of each, then the angle of the residual rotation
            Ua, _, Va = np.linalg.svd(Ra)
            Ub, _, Vb = np.linalg.svd(Rb)
            qa, qb = Ua @ Va, Ub @ Vb
            R = qa.T @ qb
            c = max(-1.0, min(1.0, (np.trace(R) - 1.0) / 2.0))
            return float(np.degrees(np.arccos(c)))

        cols = [rel('hand_l', n) for n in FORE]
        d = '' if prev is None else '%+.3f' % (p99 - prev)
        print('  f%-5d  %8.3f   %14.1f  %14.1f  %14.1f   %s'
              % (frame, p99, cols[0], cols[1], cols[2], d))
        prev = p99
print('\nPALM_DRIVER_DONE')