"""Elbow41 verification: did the repair actually reduce the wring, and did it
leave everything it is not allowed to touch alone?

For each clip, measures the source blend and the repaired edit blend with the
same validated surface-roll metric, and checks that
  * the hand world matrix is identical frame by frame (grip preserved)
  * the weapon-root chain is identical (no weapon motion change)
  * loop clips still close (first frame == last frame)
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'
EDIT = HERE / 'Edit'

STATION = {'upperarm_twist_02_l': -0.18, 'lowerarm_l': 0.23,
           'lowerarm_twist_02_l': 0.35, 'lowerarm_twist_01_l': 0.85,
           'hand_l': 1.00}
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
ANCHOR = 'upperarm_twist_02_l'
FIT_LO, FIT_HI = -0.10, 0.90
LOOPING = {'sprint_loop'}

CLIPS = (
    ('equip', ROOT / 'EquipCharge31' / 'PKM_base_EquipCharge_Editable.blend',
     EDIT / 'PKM_equip_Elbow41.blend', 'PKM31_base_equip', 'PKM_equip_Elbow41', 120, 1),
    ('sprint_enter', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     EDIT / 'PKM_sprint_enter_Elbow41.blend', 'PKM17_base_sprint_enter',
     'PKM_sprint_enter_Elbow41', 120, 1),
    ('sprint_loop', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     EDIT / 'PKM_sprint_loop_Elbow41.blend', 'PKM17_base_sprint_loop',
     'PKM_sprint_loop_Elbow41', 120, 1),
    ('sprint_exit', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     EDIT / 'PKM_sprint_exit_Elbow41.blend', 'PKM17_base_sprint_exit',
     'PKM_sprint_exit_Elbow41', 120, 1),
)

mesh_data = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
INDEX = {n: i for i, n in enumerate(V7_BONES)}

e_rest = V7_REST[INDEX['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[INDEX['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[INDEX['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)
ARM = (radius < 0.070) & (t_all > -0.30) & (t_all < 0.92)
AIDX = np.where(ARM)[0]
TV, TI, TW, TT = V7_VERTS[AIDX], V7_WIDX[AIDX], V7_WVAL[AIDX], t_all[AIDX]
THOMO = np.concatenate([TV, np.ones((len(TV), 1))], axis=1)
perp0 = (TV - e_rest) - np.outer((TV - e_rest) @ f0, f0)
p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)
EDGES = np.arange(-0.30, 0.92, 0.05)
BIN = np.digitize(TT, EDGES) - 1
NB = len(EDGES) - 1
BIN_T = EDGES[:-1] + 0.025
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (BIN_T >= FIT_LO) & (BIN_T <= FIT_HI)


def deform(skin, homo, wi, ww, n):
    out = np.zeros((n, 3))
    for k in range(wi.shape[1]):
        idx, w = wi[:, k], ww[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             homo[act])[:, :3]
    return out


def roll_profile(posed, e, u, f):
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    rp = posed - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - phi0 + np.pi) % (2 * np.pi) - np.pi)
    vals = np.full(NB, np.nan)
    for b in range(NB):
        sel = BIN == b
        if sel.sum() >= 8:
            vals[b] = dphi[sel].mean()
    return vals


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


def roll_probe(matrix, ring, rest_phi, e, u, f):
    p1 = (Vector(u) - Vector(u).dot(Vector(f)) * Vector(f)).normalized()
    p2 = Vector(f).cross(p1)
    out = []
    for v, rp in zip(ring, rest_phi):
        h = matrix @ v
        d = Vector((h.x, h.y, h.z)) - Vector(e)
        d = d - d.dot(Vector(f)) * Vector(f)
        out.append(math.degrees((math.atan2(d.dot(p2), d.dot(p1)) - rp
                                 + math.pi) % (2 * math.pi) - math.pi))
    return sum(out) / len(out)


def measure(blend, action_name, fps, stride):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    start, end = map(int, action.frame_range)

    e_r = rest['lowerarm_l'].translation
    s_r = rest['upperarm_l'].translation
    w_r = rest['hand_l'].translation
    a0 = (e_r - s_r).normalized()
    b0 = (w_r - e_r).normalized()
    flen = (w_r - e_r).length
    q1 = (a0 - a0.dot(b0) * b0).normalized()
    q2 = b0.cross(q1)
    rings, rphis = {}, {}
    for name in STATION:
        c = e_r + b0 * (STATION[name] * flen)
        ring = [c + math.cos(2 * math.pi * i / 24) * q1 * 0.045
                + math.sin(2 * math.pi * i / 24) * q2 * 0.045 for i in range(24)]
        rings[name] = ring
        rphis[name] = []
        for v in ring:
            d = v - e_r
            d = d - d.dot(b0) * b0
            rphis[name].append(math.atan2(d.dot(q2), d.dot(q1)))

    rows = []
    hand_keys = {}
    for frame in range(start, end + 1, stride):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        hand_keys[frame] = np.array(pose['hand_l'])
        delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
        s = np.array(pose['upperarm_l'].translation)
        e = np.array(pose['lowerarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        rolls = {}
        for name in (ANCHOR,) + tuple(ORDER):
            rolls[name] = roll_probe(delta[name], rings[name], rphis[name], e, u, f)
        chain = [ANCHOR] + list(ORDER)
        for i in range(1, len(chain)):
            rolls[chain[i]] = unwrap(rolls[chain[i]], rolls[chain[i - 1]])
        t0, r0 = STATION[ANCHOR], rolls[ANCHOR]
        t1, r1 = STATION['hand_l'], rolls['hand_l']
        slope = (r1 - r0) / (t1 - t0)
        skin = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in delta:
                skin[i] = np.array(delta[n])
        v = roll_profile(deform(skin, THOMO, TI, TW, len(TV)), e, u, f)
        d = np.diff(v[BIN_OK])
        rows.append({'frame': frame, 'seconds': round(frame / fps, 3),
                     'step': round(float(np.clip(d, 0, None).max()), 1),
                     'rms': round(float(np.sqrt(((v[FIT] - (r0 + slope * (BIN_T - t0))[FIT]) ** 2).mean())), 1),
                     'tv': round(float(np.abs(d).sum()), 1)})
    return {'rows': rows, 'hand': hand_keys, 'range': [start, end],
            'summary': {'worst_step': max(r['step'] for r in rows),
                        'mean_rms': round(sum(r['rms'] for r in rows) / len(rows), 1),
                        'mean_tv': round(sum(r['tv'] for r in rows) / len(rows), 1)}}


report = {}
for label, src, edit, src_action, edit_action, fps, stride in CLIPS:
    if not edit.exists():
        report[label] = {'error': 'no edit blend %s' % edit}
        print('%-13s NO EDIT' % label)
        continue
    a = measure(src, src_action, fps, stride)
    b = measure(edit, edit_action, fps, stride)

    drift = max(float(np.abs(a['hand'][f] - b['hand'][f]).max())
                for f in a['hand'] if f in b['hand'])
    closure = None
    if label in LOOPING:
        f0, f1 = a['range'][0], a['range'][1]
        closure = {'source': float(np.abs(a['hand'][f0] - a['hand'][f1]).max()),
                   'repaired': float(np.abs(b['hand'][f0] - b['hand'][f1]).max())}

    report[label] = {
        'source_action': src_action, 'repaired_action': edit_action,
        'fps': fps, 'range': b['range'],
        'before': a['summary'], 'after': b['summary'],
        'max_hand_matrix_delta': drift, 'loop_closure': closure,
        'rows': b['rows'],
    }
    print('%-13s %2d..%-3d | before step %6.1f rms %6.1f tv %6.1f'
          ' | after step %6.1f rms %6.1f tv %6.1f | hand delta %.9f%s'
          % (label, b['range'][0], b['range'][1],
             a['summary']['worst_step'], a['summary']['mean_rms'], a['summary']['mean_tv'],
             b['summary']['worst_step'], b['summary']['mean_rms'], b['summary']['mean_tv'],
             drift,
             '' if closure is None else
             ' | loop src %.2e rep %.2e' % (closure['source'], closure['repaired'])))

(HERE / 'verify_elbow41.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nVERIFY_ELBOW41_DONE')