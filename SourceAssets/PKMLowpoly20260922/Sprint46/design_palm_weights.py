"""Design the PKM palm blend-band reduction and validate it offline.

The palm's non-rigid skinning during the sprint entry comes from palm vertices blended
between hand_l and the forearm bones across a ~164 deg relative orientation.  The fix is
to shrink that blend: take a fraction of each hand-dominant vertex's forearm weight away
and give it to hand_l, so the palm rides the hand more rigidly.

Nothing here touches UE.  Skinning is a pure function of weights x bone matrices, so the
effect is fully measurable on the authored data first.  Sweeps the reduction factor and
reports, per factor:
  * palm/right-palm collapse (|B'B - I| p99), which must fall to about the idle baseline
  * the largest vertex displacement the reweight causes, which bounds the wrist-crease risk
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUTFIT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
E39 = ROOT / 'Elbow39'
spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)
AU_INDEX, AU_REST_M = E.AU_INDEX, E.AU_REST_M

D = json.loads((OUTFIT / 'Authored' / 'PKM.json').read_text(encoding='utf-8'))
# The authored JSON is in UE space: centimetres, Y flipped, relative to the author
# rig's rest space that AU_REST_M lives in (metres).  Without this the skinning math
# is off by 100x, which is what made the first displacement sweep read absurd.
POS_UE = np.array(D['positions'], dtype=np.float64)
POS = np.stack([POS_UE[:, 0] / 100.0, -POS_UE[:, 1] / 100.0, POS_UE[:, 2] / 100.0],
               axis=1)
N = len(POS)
print('authored mesh: %d verts, %d tris, source %s' % (N, len(D['triangles']), D['source']))
print('contract: %s' % D['contract'][:100])

npz = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
V = npz['verts'].astype(np.float64)
m = min(len(V), N)
nm = m
print('npz verts %d ; first %d authored verts vs npz: max |d| = %.4f m'
      % (len(V), nm, np.abs(POS[:nm] - V[:nm]).max()))

BONES = sorted({b for e in D['weights'] for b in e})
BI = {b: i for i, b in enumerate(BONES)}
W0 = np.zeros((N, len(BONES)))
for i, e in enumerate(D['weights']):
    for b, v in e.items():
        W0[i, BI[b]] = v
W0 /= np.maximum(W0.sum(axis=1, keepdims=True), 1e-9)

FORE = {s: [n for n in ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
            if n in BI] for s in ('l', 'r')}
FORE['r'] = [n.replace('_l', '_r') for n in FORE['l']]
HANDISH = {}
for s in ('l', 'r'):
    HANDISH[s] = [n for n in BONES if n.endswith('_' + s) and (
        n.startswith('hand_') or n.startswith(('thumb_', 'index_', 'middle_', 'ring_',
                                               'pinky_')))]
HOMO = np.concatenate([POS, np.ones((N, 1))], axis=1)

# palm region per side: mostly hand, not fingers
PALM = {}
for s in ('l', 'r'):
    fing = [BI[n] for n in BONES if n.endswith('_' + s) and n.startswith(
        ('thumb_0', 'index_0', 'middle_0', 'ring_0', 'pinky_0'))]
    handall = [BI[n] for n in HANDISH[s]]
    sh = W0[:, handall].sum(axis=1)
    sf = W0[:, [BI[n] for n in FORE[s]]].sum(axis=1)
    PALM[s] = np.where((sh > 0.6) & (W0[:, fing].sum(axis=1) < 0.2))[0]
    print('side %s: palm verts %d ; their forearm weight mean %.4f max %.4f'
          % (s, len(PALM[s]), sf[PALM[s]].mean(), sf[PALM[s]].max()))


def reweight(k):
    """Take (1-k) of every hand-dominant vertex's forearm weight and give it to hand_l."""
    W = W0.copy()
    for s in ('l', 'r'):
        handbone = BI['hand_' + s]
        fidx = [BI[n] for n in FORE[s]]
        handall = [BI[n] for n in HANDISH[s]]
        sh = W0[:, handall].sum(axis=1)
        sel = np.where(sh > 0.5)[0]
        sf = W[:, fidx].sum(axis=1)
        moved = sf[sel] * (1.0 - k)
        W[np.ix_(sel, fidx)] *= k
        W[sel, handbone] += moved
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-9)
    return W


def skin_matrices(rig, scene, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
    S = np.tile(np.eye(4), (len(BONES), 1, 1))
    for i, n in enumerate(BONES):
        if n in pose:
            S[i] = pose[n] @ np.linalg.inv(np.array(AU_REST_M[AU_INDEX[n]]))
    return S


def evaluate(W, S, sel):
    B = np.einsum('vb,bij->vij', W[sel], S[:, :3, :3])
    M = np.einsum('vji,vjk->vik', B, B) - np.eye(3)
    return float(np.percentile(np.linalg.norm(M, axis=(1, 2)), 99))


def skinned(W, S):
    P = np.zeros((N, 3))
    for b in range(len(BONES)):
        w = W[:, b]
        nz = w > 0
        if not nz.any():
            continue
        P[nz] += w[nz, None] * np.einsum('ij,vj->vi', S[b], HOMO[nz])[:, :3]
    return P


CLIPS = (
    ('idle', ROOT / 'Elbow42' / 'Edit' / 'PKM_idle_Elbow42.blend', 'PKM_idle_Elbow42', 60),
    ('sprint', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
     'PKM_sprint_enter_Sprint44', 120),
)
FRAMES = {'idle': None, 'sprint': list(range(0, 11))}

FACTORS = (1.0, 0.75, 0.5, 0.35, 0.25, 0.15, 0.0)
report = {}
for tag, blend, action, fps in CLIPS:
    if not blend.exists():
        print('MISSING %s' % blend)
        continue
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = fps
    start, end = map(int, act.frame_range)
    want = FRAMES[tag] or list(range(start, end + 1))
    frames = [f for f in want if start <= f <= end]
    mats = {f: skin_matrices(rig, scene, f) for f in frames}
    base = {f: skinned(W0, mats[f]) for f in frames}
    print('\n=== %s (%s) frames %s ===' % (tag, action, frames[:12]))
    print('  k      L-palm   R-palm   L-p50   L-p99   L-max   R-max   all-max  (mm)')
    rows = {}
    for k in FACTORS:
        W = reweight(k)
        lp = max(evaluate(W, mats[f], PALM['l']) for f in frames)
        rp = max(evaluate(W, mats[f], PALM['r']) for f in frames)
        dl = dr = da = 0.0
        q50 = q99 = 0.0
        for f in frames:
            if k == 1.0:
                continue
            d = np.linalg.norm(skinned(W, mats[f]) - base[f], axis=1) * 1000.0
            q50 = max(q50, float(np.percentile(d[PALM['l']], 50)))
            q99 = max(q99, float(np.percentile(d[PALM['l']], 99)))
            dl = max(dl, float(d[PALM['l']].max()))
            dr = max(dr, float(d[PALM['r']].max()))
            da = max(da, float(d.max()))
        rows[k] = {'L_palm': round(lp, 4), 'R_palm': round(rp, 4),
                   'L_p50_mm': round(q50, 3), 'L_p99_mm': round(q99, 3),
                   'L_disp_mm': round(dl, 3), 'R_disp_mm': round(dr, 3),
                   'all_disp_mm': round(da, 3)}
        print('  %-5s  %7.4f  %7.4f  %6.2f  %6.2f  %6.2f  %6.2f  %7.2f'
              % (k, lp, rp, q50, q99, dl, dr, da))
    report[tag] = rows

(ROOT / 'Sprint46' / 'reweight_sweep.json').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'Sprint46' / 'reweight_sweep.json').write_text(
    json.dumps({'factors': list(FACTORS), 'clips': report}, indent=2), encoding='utf-8')
print('\nREWEIGHT_SWEEP_DONE')