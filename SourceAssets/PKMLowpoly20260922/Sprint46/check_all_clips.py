"""Full regression check: does the palm reweight hurt any accepted PKM clip?

Weights are a mesh property, so the reweight applies to EVERY PKM clip, not just the
sprint.  This evaluates every shipped-or-candidate PKM clip under both the original and
the reweighted skin and reports the palm's linear-blend non-rigidity (p99 of
|B'B - I|) plus how far the reweight moves the worst vertex.  A clip that regresses
would show its collapse going UP.
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


def load_doc(path):
    d = json.loads(path.read_text(encoding='utf-8'))
    P = np.array(d['positions'], dtype=np.float64)
    P = np.stack([P[:, 0] / 100.0, -P[:, 1] / 100.0, P[:, 2] / 100.0], axis=1)
    return d, P


DOC_OLD, POS = load_doc(ROOT / 'Sprint46' / 'Before' / 'PKM.json')
DOC_NEW, _ = load_doc(OUTFIT / 'Authored' / 'PKM.json')
BONES = sorted({b for e in DOC_OLD['weights'] for b in e})
BI = {b: i for i, b in enumerate(BONES)}


def dense(doc):
    W = np.zeros((len(doc['weights']), len(BONES)))
    for i, e in enumerate(doc['weights']):
        for b, v in e.items():
            W[i, BI[b]] = v
    return W / np.maximum(W.sum(axis=1, keepdims=True), 1e-9)


W_OLD, W_NEW = dense(DOC_OLD), dense(DOC_NEW)

FORE = {s: ['lowerarm_%s' % s, 'lowerarm_twist_01_%s' % s, 'lowerarm_twist_02_%s' % s]
        for s in ('l', 'r')}
HANDISH = {s: [b for b in BONES if b.endswith('_' + s) and (
    b.startswith('hand_') or b.startswith(('thumb_', 'index_', 'middle_', 'ring_',
                                           'pinky_')))] for s in ('l', 'r')}
PALM = {}
for s in ('l', 'r'):
    fing = [BI[b] for b in BONES if b.endswith('_' + s) and b.startswith(
        ('thumb_0', 'index_0', 'middle_0', 'ring_0', 'pinky_0'))]
    sh = W_OLD[:, [BI[b] for b in HANDISH[s]]].sum(axis=1)
    PALM[s] = np.where((sh > 0.6) & (W_OLD[:, fing].sum(axis=1) < 0.2))[0]
HOMO = np.concatenate([POS, np.ones((len(POS), 1))], axis=1)

CLIPS = (
    ('idle', ROOT / 'Elbow42' / 'Edit' / 'PKM_idle_Elbow42.blend', 'PKM_idle_Elbow42', 60),
    ('equip', ROOT / 'Elbow41' / 'Edit' / 'PKM_equip_Elbow41.blend', 'PKM_equip_Elbow41', 60),
    ('reload', ROOT / 'Elbow39' / 'Edit' / 'PKM_reload_Elbow39.blend',
     'PKM_reload_Elbow39', 60),
    ('reload_empty', ROOT / 'Elbow39' / 'Edit' / 'PKM_reload_empty_Elbow39.blend',
     'PKM_reload_empty_Elbow39', 60),
    ('sprint_enter', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_enter_Sprint44.blend',
     'PKM_sprint_enter_Sprint44', 120),
    ('sprint_loop', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_loop_Sprint44.blend',
     'PKM_sprint_loop_Sprint44', 120),
    ('sprint_exit', ROOT / 'Sprint44' / 'Edit' / 'PKM_sprint_exit_Sprint44.blend',
     'PKM_sprint_exit_Sprint44', 120),
)


def collapse(W, S, sel):
    B = np.einsum('vb,bij->vij', W[sel], S[:, :3, :3])
    M = np.einsum('vji,vjk->vik', B, B) - np.eye(3)
    return float(np.percentile(np.linalg.norm(M, axis=(1, 2)), 99))


def skinned(W, S):
    P = np.zeros((len(POS), 3))
    for b in range(len(BONES)):
        w = W[:, b]
        nz = w > 0
        if nz.any():
            P[nz] += w[nz, None] * np.einsum('ij,vj->vi', S[b], HOMO[nz])[:, :3]
    return P


report = {}
print('%-14s %8s %8s %11s %11s %10s' % (
    'clip', 'oldL', 'newL', 'oldMaxFrame', 'newMaxFrame', 'worstMove'))
print('%-14s %8s %8s %11s %11s %10s' % (
    '', '(p99)', '(p99)', '(frame)', '(frame)', '(mm)'))
for tag, blend, action, fps in CLIPS:
    if not blend.exists():
        print('%-14s MISSING %s' % (tag, blend.name))
        continue
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = fps
    start, end = map(int, act.frame_range)
    oldL = newL = 0.0
    oldF = newF = -1
    move = 0.0
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: np.array(rig.pose.bones[b.name].matrix) for b in rig.pose.bones}
        S = np.tile(np.eye(4), (len(BONES), 1, 1))
        for i, n in enumerate(BONES):
            if n in pose:
                S[i] = pose[n] @ np.linalg.inv(np.array(AU_REST_M[AU_INDEX[n]]))
        a, b = collapse(W_OLD, S, PALM['l']), collapse(W_NEW, S, PALM['l'])
        if a > oldL:
            oldL, oldF = a, frame
        if b > newL:
            newL, newF = b, frame
        d = np.linalg.norm(skinned(W_NEW, S) - skinned(W_OLD, S), axis=1) * 1000.0
        move = max(move, float(d.max()))
    report[tag] = {'old_p99': round(oldL, 4), 'new_p99': round(newL, 4),
                   'old_at': oldF, 'new_at': newF, 'worst_move_mm': round(move, 2),
                   'frames': end - start + 1}
    flag = 'OK ' if newL <= oldL + 1e-6 else 'UP!'
    print('%-14s %8.4f %8.4f %11s %11s %10.2f  %s'
          % (tag, oldL, newL, 'f%d' % oldF, 'f%d' % newF, move, flag))

(ROOT / 'Sprint46' / 'regression_check.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print('\nREGRESSION_CHECK_DONE')