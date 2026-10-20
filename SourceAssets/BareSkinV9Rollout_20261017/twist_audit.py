"""Forearm twist audit of a batch's clips: how much of the hand's roll about the forearm the twist bones carry.

For every clip frame and side: hand, lowerarm_twist_01 and lowerarm_twist_02 roll about the forearm axis,
each relative to lowerarm and to the bind pose (swing-twist decomposition). A wrist "candy wrapper" shows up
as a hand roll the wrist-side twist bone does not follow. Writes Work/<batch>_twist.json.
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rollout import R, load_snapshot

BATCH = sys.argv[1] if len(sys.argv) > 1 else 'batch1'
CLIPS = sys.argv[2] if len(sys.argv) > 2 else 'Clips'
plan = json.loads((R / (BATCH + '.json')).read_text())


def twist_angle(q_rel, axis):
    """Signed twist (deg) of rotation q_rel about unit axis (swing-twist)."""
    x, y, z, w = q_rel.as_quat()
    if w < 0: x, y, z, w = -x, -y, -z, -w
    proj = np.dot([x, y, z], axis)
    return float(np.degrees(2 * np.arctan2(proj, w)))


def wrap(a): return (np.asarray(a) + 180) % 360 - 180


out = {}
for name, vm in plan['viewmodels'].items():
    f = R / CLIPS / (name + '.json')
    if not f.exists(): continue
    cd = json.loads(f.read_text()); bones = cd['bones']; bi = {b: i for i, b in enumerate(bones)}
    ref = load_snapshot(vm)['bones']
    res = {}
    for s in ('l', 'r'):
        need = ['lowerarm_' + s, 'hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s]
        if not all(b in bi and b in ref for b in need): continue
        rq = {b: Rot.from_quat(ref[b]['q']) for b in need}; rt = {b: np.array(ref[b]['t']) for b in need}
        L = 'lowerarm_' + s
        axis_c = rt['hand_' + s] - rt[L]; axis_c /= np.linalg.norm(axis_c)
        axis_l = rq[L].inv().apply(axis_c)                                     # forearm axis in lowerarm local
        rel_ref = {b: rq[L].inv() * rq[b] for b in need[1:]}
        frac = {b: float((rt[b] - rt[L]) @ axis_c / np.linalg.norm(rt['hand_' + s] - rt[L])) for b in need[2:]}
        for path, c in cd['clips'].items():
            if 'frames' not in c: continue
            rows = []
            for fr in c['frames']:
                q = {b: Rot.from_quat(fr[bi[b]][3:]) for b in need}
                th = {b: twist_angle((q[L].inv() * q[b]) * rel_ref[b].inv(), axis_l) for b in need[1:]}
                rows.append([th['hand_' + s], th['lowerarm_twist_01_' + s], th['lowerarm_twist_02_' + s]])
            a = np.array(rows); big = np.abs(a[:, 0]) > 10
            res.setdefault(path.split('/')[-1] + ':' + path, {})[s] = dict(
                hand=[round(float(a[:, 0].min()), 1), round(float(a[:, 0].max()), 1)],
                t1_minus_hand=round(float(np.abs(wrap(a[:, 1] - a[:, 0])).max()), 1),
                t2_minus_half=round(float(np.abs(wrap(a[:, 2] - .5 * a[:, 0])).max()), 1),
                t1_share=round(float(np.median(a[big, 1] / a[big, 0])), 2) if big.any() else None,
                t2_share=round(float(np.median(a[big, 2] / a[big, 0])), 2) if big.any() else None,
                frac=frac)
    out[name] = res
    worst = sorted(((v[s]['t1_minus_hand'], k.split(':')[0], s) for k, v in res.items() for s in v), reverse=True)[:6]
    print(name, 'twist bone positions (fraction elbow->wrist)', {k[:20]: round(v, 2) for k, v in (res[next(iter(res))].get('l', {}) or {}).get('frac', {}).items()} if res else '',
          '| worst |twist_01 - hand|:', worst, flush=True)
(R / 'Work').mkdir(exist_ok=True)
(R / 'Work' / (BATCH + ('_twist.json' if CLIPS in ('Clips', 'ClipsTrue') else '_twist_after.json'))).write_text(json.dumps(out, indent=1))


