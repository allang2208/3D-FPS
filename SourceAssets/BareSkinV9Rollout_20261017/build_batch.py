"""Offline build of one rollout batch: V9 surface transfer + joint correctives + held grips per mesh,
forearm twist redistribution plan per clip, validation on the (twist-fixed) shipped clips.

Usage: python build_batch.py batch1 [mesh substring ...]   -> Work/<batch>/<key>.json (+ .npz), twist plan
"""
import sys, json, time, traceback
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, M4Source, load_snapshot, key_of
from transfer import M4Index, transfer, weld
from jc import Rig, Driver, grip_examples, validate, frame_pose
from twist_fix import SideTwist

import os
BATCH = sys.argv[1]; only = sys.argv[2:]
plan = json.loads((R / (BATCH + '.json')).read_text())
OUT = R / 'Work' / BATCH; OUT.mkdir(parents=True, exist_ok=True)
audit = json.loads((R / 'Work' / (BATCH + '_twist.json')).read_text())
src = M4Source(); ix = M4Index(src)
# clips as installed (ClipsAfter, data-model reader): twist already redistributed, nothing to simulate
CLIPSRC = os.environ.get('V9R_CLIPSRC', 'Clips')


def flagged(pose_src):
    """clip path -> sides whose forearm twist the clip gets wrong (twist_01 != hand roll, twist_02 != half)."""
    if CLIPSRC in ('ClipsAfter', 'ClipsSim'): return {}       # twist already in the clip data
    out = {}
    for k, sides in audit.get(pose_src, {}).items():
        path = k.split(':', 1)[1]
        bad = [s for s, x in sides.items() if x['t1_minus_hand'] > 15 or x['t2_minus_half'] > 10]
        if bad: out[path] = bad
    return out


clip_cache = {}
def clips_fixed(pose_src):
    """Pose-source clips with the twist redistribution applied to the flagged sides (as UE will store them)."""
    if pose_src in clip_cache: return clip_cache[pose_src]
    cd = json.loads((R / CLIPSRC / (pose_src + '.json')).read_text()); bones = cd['bones']; bi = {b: i for i, b in enumerate(bones)}
    ref = load_snapshot(plan['viewmodels'][pose_src])['bones']; fl = flagged(pose_src)
    for path, sides in fl.items():
        c = cd['clips'].get(path)
        if not c or 'frames' not in c: continue
        for s in sides:
            st = SideTwist(ref, s); L = bi['lowerarm_' + s]; H = bi['hand_' + s]
            qL = [Rot.from_quat(fr[L][3:]) for fr in c['frames']]; qH = [Rot.from_quat(fr[H][3:]) for fr in c['frames']]
            loc = st.twist_locals(st.hand_rolls(qL, qH))
            for b, rots in loc.items():
                if b not in bi: continue
                for fi, fr in enumerate(c['frames']):
                    fr[bi[b]] = fr[bi[b]][:3] + list((qL[fi] * rots[fi]).as_quat())
    clip_cache[pose_src] = (cd, fl)
    return clip_cache[pose_src]


def geo_normals(rig, X):
    return rig.vnormals(X)


def rotate(v, a, b):
    ax = np.cross(a, b); s = np.linalg.norm(ax); c = a @ b
    if s < 1e-9: return v
    ax /= s; th = np.arctan2(s, c)
    return v * np.cos(th) + np.cross(ax, v) * np.sin(th) + ax * (ax @ v) * (1 - np.cos(th))


HELD_SKIP = ('reload', 'inspect', 'sprint', 'equip', 'walk', 'run', 'turn', 'jump', 'land', 'melee', 'combat', 'fire', 'attack', 'charge', 'draw',
             'holster', 'break', 'hit', 'enter', 'exit', 'preview', 'before')


def held_of(ps, cd):
    """Held (persistent) poses: the plan's list, else every idle / hold / ready / guard clip of the pose source."""
    if plan['held'].get(ps): return plan['held'][ps]
    out = []
    for path, c in cd['clips'].items():
        n_ = '_'.join(path.split('/')[-1].lower().split('_')[2:])     # drop "A_<weapon>_" (RuneSword contains "run")
        if 'frames' in c and (any(k in n_ for k in ('idle', 'hold', 'ready')) or n_ == 'guard' or n_.endswith('_guard')) and not any(k in n_ for k in HELD_SKIP):
            out.append(path)
    return out


twist_plan = {}
for entry in plan['meshes']:
    pk = entry['mesh']
    if only and not any(o in pk for o in only): continue
    key = key_of(pk); dst = OUT / (key + '.json')
    if dst.exists(): print('skip', pk); continue
    missing = [s_ for s_ in (entry.get('pose_sources') or [entry.get('pose_source')]) if not (R / CLIPSRC / (s_ + '.json')).exists()]
    if missing: print('wait', pk, 'clips not read yet:', missing); continue
    t0 = time.time()
    try:
        t = load_snapshot(pk)
        if entry.get('morphs_only'):
            # already V9 (the accepted M4 sample): no surface change, only the held grips it does not have yet
            Xs = np.array(t['positions']); tr = dict(positions=Xs, weights={}, region=np.zeros(len(t['triangles']), int), normals=np.array(t['normals']),
                                                      uv0=np.array(t['uv0']), stats=dict(matched=len(t['triangles']), fallback=0, pinholes_before=0, pinholes_after=0))
            Tm = np.array(t['triangles']); src_reg = {tuple(sorted(r)): src.region[i] for i, r in enumerate(src.weld[src.T])}
            wm, _ = weld(Xs); m4w = {tuple(np.round(p_, 4)): i for i, p_ in enumerate(ix.P9)}
            for i, tri in enumerate(Tm):
                k_ = tuple(sorted(m4w.get(tuple(np.round(Xs[v], 4)), -1) for v in tri)); tr['region'][i] = src_reg.get(k_, 2)
        elif entry.get('template'):
            from rederive import rederive
            tr = rederive(t, entry['template'], ix)        # distorted FBX-family skin: rebuilt from a clean sibling
        else:
            tr = transfer(t, ix)
        X = tr['positions']; T = np.array(t['triangles'])
        w, n = weld(X); P = np.zeros((n, 3)); P[w] = X
        W = [dict(r) for r in t['weights']]
        for v, row in tr['weights'].items(): W[int(v)] = row
        Ww = [None] * n
        for v in range(len(X)): Ww[w[v]] = W[v]
        regw = np.zeros(n, int)
        for i, tri in enumerate(T):
            for v in tri: regw[w[v]] = max(regw[w[v]], tr['region'][i])
        sg = np.sign(np.einsum('ij,ij->', np.cross(X[T[:, 1]] - X[T[:, 0]], X[T[:, 2]] - X[T[:, 0]]), np.array(t['normals']).mean(axis=1))) or 1.0
        rig = Rig(P, w[T], Ww, regw, t['bones'], sg)
        log = []
        shapes, meta = rig.joint_keys(log=lambda *a: log.append(' '.join(map(str, a))))
        sources = entry.get('pose_sources') or [entry['pose_source']]
        ps = sources[0]
        leader = load_snapshot(plan['viewmodels'][ps])['bones']
        driver = Driver(leader)
        for s_ in sources:
            if not (R / CLIPSRC / (s_ + '.json')).exists(): continue
            cd, fl = clips_fixed(s_); twist_plan[s_] = fl
            grips, gmeta = grip_examples(rig, driver, shapes, held_of(s_, cd), cd, log=lambda *a: log.append(' '.join(map(str, a))),
                                         existing=[n_ for n_ in shapes if n_.startswith('JC_Grip_')])
            shapes.update(grips); meta.update(gmeta)
        vshapes = dict(shapes)
        if entry.get('morphs_only'):
            keep = set(t['morphs'])
            shapes = {k_: v_ for k_, v_ in shapes.items() if k_.startswith('JC_Grip_') and k_ not in keep and
                      not any(e_.startswith(k_[:9]) and np.linalg.norm(np.array([float(x) for x in e_.split('_')[3:7]]) - np.array([float(x) for x in k_.split('_')[3:7]])) < 8
                              for e_ in keep if e_.startswith('JC_Grip_'))}
            meta = {k_: v_ for k_, v_ in meta.items() if k_ in shapes}
        driver = Driver(leader, [n_ for n_ in vshapes if n_.startswith('JC_Grip_')])
        report = {}
        for s_ in sources:
            if not (R / CLIPSRC / (s_ + '.json')).exists(): continue
            cd, _ = clips_fixed(s_)
            for k_, v_ in validate(rig, driver, vshapes, cd, every=4 if len(sources) == 1 else 8).items(): report[k_ if len(sources) == 1 else s_ + ':' + k_] = v_
        # payload: split-vertex positions / normals, corner UV0, weights, morph rows
        VN = np.zeros((len(X), 3))
        for i, tri in enumerate(T):
            for c in range(3): VN[tri[c]] += tr['normals'][i, c]
        VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)
        G0 = rig.vnormals(P); morph_rows = {}
        for name, d in shapes.items():
            moved = np.linalg.norm(d, axis=1) > .012
            if not moved.any(): continue
            G1 = rig.vnormals(P + d); rows = []
            for v in range(len(X)):
                if not moved[w[v]]: continue
                nn = rotate(VN[v], G0[w[v]], G1[w[v]]); nn /= np.linalg.norm(nn)
                rows.append([int(t['vertex_ids'][v]), *map(float, X[v] + d[w[v]]), *map(float, nn)])
            morph_rows[name] = rows
        payload = dict(path=pk, key=key, sha=t['sha'], lods=t['lods'], pose_source=ps, pose_sources=sources, morphs_only=bool(entry.get('morphs_only')),
                       keep=list(t['morphs']) if entry.get('morphs_only') else [], stale_prefix='JC_Grip_' if entry.get('morphs_only') else None,
                       skin_slots=[i for i, s in enumerate(t['slots']) if s['skin']], slots=t['slots'],
                       vertex_ids=[int(v) for v in t['vertex_ids']], old_positions=np.round(np.array(t['positions']), 6).tolist(),
                       positions=np.round(X, 6).tolist(), vertex_normals=np.round(VN, 6).tolist(),
                       triangle_ids=[int(i) for i in t['triangle_ids']], uv0=np.round(tr['uv0'], 7).tolist(),
                       weights={str(int(t['vertex_ids'][v])): row for v, row in tr['weights'].items()}, morphs=morph_rows,
                       stats=tr['stats'], correctives={k: v for k, v in meta.items()}, validation=report, log=log)
        dst.write_text(json.dumps(payload))
        worst = max(report.items(), key=lambda kv: kv[1]['corrected']) if report else ('', {})
        print('%-70s %4.0fs %s shapes %d | worst pinholes %s %s | idle %s' % (pk[-70:], time.time() - t0, json.dumps({k: tr['stats'][k] for k in ('matched', 'fallback', 'pinholes_before', 'pinholes_after')}),
              len(morph_rows), worst[0], worst[1], {k: v for k, v in report.items() if k.lower().endswith(('idle', 'hold', 'ready', '_guard'))}), flush=True)
    except Exception:
        (OUT / (key + '.error.txt')).write_text(traceback.format_exc()); print('FAILED', pk, traceback.format_exc().splitlines()[-1], flush=True)
existing = json.loads((OUT / 'twist_plan.json').read_text()) if (OUT / 'twist_plan.json').exists() else {}
existing.update(twist_plan)
(OUT / 'twist_plan.json').write_text(json.dumps(existing, indent=1))

