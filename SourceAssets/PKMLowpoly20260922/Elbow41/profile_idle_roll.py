"""Roll profile along the forearm: shipped PKM idle, left against right.

Same surface-roll measure used everywhere else, but printed bin by bin for both
arms so the left arm's defect can be read off directly against the right arm,
which deforms cleanly in the same frame of the same clip.
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

BLEND = E39 / 'Edit' / 'PKM_idle_Elbow39.blend'
ACTION = 'PKM_idle_Elbow39'
FPS = 60
FRAMES = [0, 30, 60]
STATION = {'upperarm_twist_02': -0.18, 'lowerarm': 0.23,
           'lowerarm_twist_02': 0.35, 'lowerarm_twist_01': 0.85, 'hand': 1.00}

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])
REST = d['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: i for i, n in enumerate(BONES)}

EDGES = np.arange(-0.30, 0.92, 0.05)
NB = len(EDGES) - 1
BIN_T = EDGES[:-1] + 0.025


def side_setup(s):
    e = REST[IDX['lowerarm_%s' % s]][:3, 3].copy()
    sh = REST[IDX['upperarm_%s' % s]][:3, 3].copy()
    w = REST[IDX['hand_%s' % s]][:3, 3].copy()
    u0 = (e - sh) / np.linalg.norm(e - sh)
    f0 = (w - e) / np.linalg.norm(w - e)
    flen = float(np.linalg.norm(w - e))
    rel = V - e
    t = rel @ f0 / flen
    rad = np.linalg.norm(rel - np.outer(t * flen, f0), axis=1)
    sel = (rad < 0.075) & (t > -0.30) & (t < 0.92)
    vs = np.where(sel)[0]
    perp = (V[vs] - e) - np.outer((V[vs] - e) @ f0, f0)
    p1 = u0 - (u0 @ f0) * f0
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f0, p1)
    phi0 = np.arctan2(perp @ p2, perp @ p1)
    bin_ = np.digitize(t[vs], EDGES) - 1
    ok = np.array([(bin_ == b).sum() >= 8 for b in range(NB)])
    return {'e': e, 'sh': sh, 'w': w, 'f0': f0, 'flen': flen, 'vs': vs,
            'phi0': phi0, 'bin': bin_, 'ok': ok,
            'rrings': {}, 'rphis': {}}


def ring(s, st):
    """Probe ring of 24 points at a station along the forearm."""
    S = st['e'] + st['f0'] * (st['flen'] * STATION[s])
    a0 = (st['e'] - st['sh']) / np.linalg.norm(st['e'] - st['sh'])
    q1 = a0 - (a0 @ st['f0']) * st['f0']
    q1 /= np.linalg.norm(q1)
    q2 = np.cross(st['f0'], q1)
    pts = [S + math.cos(2 * math.pi * i / 24) * q1 * 0.045
           + math.sin(2 * math.pi * i / 24) * q2 * 0.045 for i in range(24)]
    ph = []
    for v in pts:
        dd = v - st['e']
        dd = dd - (dd @ st['f0']) * st['f0']
        ph.append(math.atan2(dd @ q2, dd @ q1))
    return pts, ph


def probe(matrix, pts, ph, e, u, f):
    p1 = (Vector(u) - Vector(u).dot(Vector(f)) * Vector(f)).normalized()
    p2 = Vector(f).cross(p1)
    out = []
    for v, rp in zip(pts, ph):
        h = matrix @ Vector((float(v[0]), float(v[1]), float(v[2])))
        dd = Vector((h.x, h.y, h.z)) - Vector(e)
        dd = dd - dd.dot(Vector(f)) * Vector(f)
        out.append(math.degrees((math.atan2(dd.dot(p2), dd.dot(p1)) - rp
                                 + math.pi) % (2 * math.pi) - math.pi))
    return sum(out) / len(out)


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


def profile(posed, st, e, u, f):
    rp = posed - e
    pp = rp - np.outer(rp @ f, f)
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - st['phi0'] + np.pi) % (2 * np.pi) - np.pi)
    out = np.full(NB, np.nan)
    for b in range(NB):
        sel = st['bin'] == b
        if sel.sum() >= 8:
            out[b] = dphi[sel].mean()
    return out


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = FPS

SETUP = {s: side_setup(s) for s in ('l', 'r')}
RINGS = {}
for s in ('l', 'r'):
    for k in STATION:
        RINGS[(s, k)] = ring(k, SETUP[s])

CHAIN = ['upperarm_twist_02', 'lowerarm', 'lowerarm_twist_02',
         'lowerarm_twist_01', 'hand']

out = {}
for frame in FRAMES:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}

    print('\n================ frame %d (%.2fs) ================' % (frame, frame / FPS))
    prof = {}
    for s in ('l', 'r'):
        st = SETUP[s]
        e = np.array(pose['lowerarm_%s' % s].translation)
        sh = np.array(pose['upperarm_%s' % s].translation)
        w = np.array(pose['hand_%s' % s].translation)
        u = (e - sh) / np.linalg.norm(e - sh)
        f = (w - e) / np.linalg.norm(w - e)
        rolls = {}
        for k in CHAIN:
            bone = k + '_' + s
            rolls[k] = probe(delta[bone], *RINGS[(s, k)], e=e, u=u, f=f)
        for i in range(1, len(CHAIN)):
            rolls[CHAIN[i]] = unwrap(rolls[CHAIN[i]], rolls[CHAIN[i - 1]])
        bend = math.degrees(math.acos(max(-1, min(1, float(u @ f)))))
        prof[s] = {'rolls': rolls, 'e': e, 'u': u, 'f': f, 'bend': bend}

    print('  left elbow bend %.1f deg   right %.1f deg'
          % (prof['l']['bend'], prof['r']['bend']))
    print('  station rolls (degrees about the live forearm axis)')
    print('    %-22s %10s %10s' % ('station', 'LEFT', 'RIGHT'))
    for k in CHAIN:
        print('    %-22s %10.1f %10.1f'
              % (k, prof['l']['rolls'][k], prof['r']['rolls'][k]))
    print('  pronation available (hand - elbow side): L %.1f  R %.1f'
          % (prof['l']['rolls']['hand'] - prof['l']['rolls']['upperarm_twist_02'],
             prof['r']['rolls']['hand'] - prof['r']['rolls']['upperarm_twist_02']))

    for s, label in (('l', 'LEFT'), ('r', 'RIGHT')):
        st = SETUP[s]
        skin = np.tile(np.eye(4), (len(BONES), 1, 1))
        for i, n in enumerate(BONES):
            if n in delta:
                skin[i] = np.array(delta[n])
        homo = np.concatenate([V[st['vs']], np.ones((len(st['vs']), 1))], axis=1)
        posed = np.zeros((len(st['vs']), 3))
        for k in range(WIDX.shape[1]):
            idx, w = WIDX[st['vs'], k], WVAL[st['vs'], k]
            a = (idx >= 0) & (w > 0)
            posed[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], homo[a])[:, :3]
        p = profile(posed, st, prof[s]['e'], prof[s]['u'], prof[s]['f'])
        d = np.diff(p[st['ok']])
        print('  %s surface profile: worst step %6.1f  total variation %6.1f'
              % (label, float(np.clip(d, 0, None).max()), float(np.abs(d).sum())))
        if s == 'l':
            out['profile_left'] = [None if np.isnan(x) else round(float(x), 1) for x in p]
            out['steps_left'] = [round(float(x), 1) for x in d]
        else:
            out['profile_right'] = [None if np.isnan(x) else round(float(x), 1) for x in p]
            out['steps_right'] = [round(float(x), 1) for x in d]

    if frame == FRAMES[0]:
        print('\n  bin t     LEFT dphi   step |  RIGHT dphi   step')
        dl, dr = out['steps_left'], out['steps_right']
        for b in range(NB):
            a = out['profile_left'][b]
            c = out['profile_right'][b]
            print('  %6.3f  %10s %6s | %10s %6s'
                  % (BIN_T[b],
                     'nan' if a is None else '%8.1f' % a, '%6.1f' % dl[b] if b < len(dl) else '',
                     'nan' if c is None else '%8.1f' % c, '%6.1f' % dr[b] if b < len(dr) else ''))

(HERE / 'idle_roll_profile.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('\nIDLE_ROLL_PROFILE_DONE')