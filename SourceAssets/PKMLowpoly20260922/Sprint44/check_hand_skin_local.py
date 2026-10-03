"""Localise the hand's non-rigid skinning: which part, which frames."""
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
FINGER = {n for n in V7_BONES if n.endswith('_l') and n.startswith(
    ('thumb_0', 'index_0', 'middle_0', 'ring_0', 'pinky_0'))}
PALM = {n for n in V7_BONES if n == 'hand_l' or n.endswith('_metacarpal_l')}
fi = [V7_BONES.index(n) for n in FINGER]
pi = [V7_BONES.index(n) for n in PALM]
fsh, psh = W[:, fi].sum(axis=1), W[:, pi].sum(axis=1)
FING = np.where(fsh > 0.6)[0]
PALMV = np.where((psh > 0.6) & (fsh < 0.2))[0]
print('finger verts %d   palm verts %d' % (len(FING), len(PALMV)))

CASES = (('idle', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
          'PKM_Game_idle', 60),
         ('sprint_original', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
          'PKM17_base_sprint_enter', 120),
         ('sprint_sprint44', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
          'PKM_sprint_enter_Sprint44', 120))

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
    rows = {}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
        skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in pose:
                skin[i] = pose[n] @ np.linalg.inv(np.array(E.AU_REST_M[AU_INDEX[n]]))
        for nm, sel in (('finger', FING), ('palm', PALMV)):
            B = np.zeros((len(sel), 3, 3))
            for k in range(WIDX.shape[1]):
                idx, w = WIDX[sel, k], WVAL[sel, k]
                a = (idx >= 0) & (w > 0)
                B[a] += w[a, None, None] * skin[idx[a]][:, :3, :3]
            M = np.einsum('nji,njk->nik', B, B) - np.eye(3)
            e = np.linalg.norm(M, axis=(1, 2))
            rows.setdefault(nm, {})[frame] = (float(e.mean()), float(np.percentile(e, 99)))
    summary = {}
    for nm in ('finger', 'palm'):
        r = rows[nm]
        wf = max(r, key=lambda f: r[f][1])
        summary[nm] = {'worst_p99': round(r[wf][1], 4), 'at_frame': wf,
                       'worst_mean': round(max(v[0] for v in r.values()), 4)}
    out[tag] = summary
    print('\n%s' % tag)
    for nm in ('finger', 'palm'):
        print('   %-7s worst p99 %.4f (f%d)  worst mean %.4f'
              % (nm, summary[nm]['worst_p99'], summary[nm]['at_frame'],
                 summary[nm]['worst_mean']))
    if tag.startswith('sprint'):
        print('   frame:  ' + '  '.join('f%-5d' % f for f in range(start, min(start + 16, end + 1))))
        for nm in ('finger', 'palm'):
            print('   %-6s: ' % nm + '  '.join('%.3f' % rows[nm][f][1]
                                               for f in range(start, min(start + 16, end + 1))))

(ROOT / 'Sprint44' / 'hand_skin_local.json').write_text(
    json.dumps(out, indent=2), encoding='utf-8')
print('\nHAND_SKIN_LOCAL_DONE')