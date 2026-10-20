"""Offline: compare the render material (slot name) of every triangle now vs the Before/ original (matched by
centroid). -> Work/matprobe_report.json {key: {path, mismatched, total, by_pair, fix: {now_tri_index: slot_index_now}}}"""
import json, collections
import numpy as np
from scipy.spatial import cKDTree
from rollout import R

import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else 'Work/MatProbe'; DST = sys.argv[2] if len(sys.argv) > 2 else 'Work/matprobe_report.json'
report = {}
for f in sorted((R / SRC).glob('*.json')):
    d = json.loads(f.read_text())
    if d.get('error') or not d.get('render_now') or not d.get('render_before'):
        report[f.stem] = dict(path=d['path'], error=d.get('error', 'no render data')); continue
    now = np.array(d['render_now']); old = np.array(d['render_before'])
    # slot names compared case-insensitively (the install wrote the imported names: 'tritium' vs 'Tritium')
    sn = [x.lower() for x in d['slots_now']]; sb = [x.lower() for x in d['slots_before']]
    tree = cKDTree(old[:, 1:]); dist, idx = tree.query(now[:, 1:], k=4, distance_upper_bound=0.05)
    name_now = [sn[int(m)] if int(m) < len(sn) else '?' for m in now[:, 0]]
    name_old = []; close = np.zeros(len(now), bool)
    for t in range(len(now)):
        cand = {sb[int(old[i, 0])] if int(old[i, 0]) < len(sb) else '?' for dd, i in zip(dist[t], idx[t]) if np.isfinite(dd)}
        # coincident duplicates with different materials (e.g. PKM old / new belt) are ambiguous: left alone
        if len(cand) == 1: name_old.append(cand.pop()); close[t] = True
        else: name_old.append(name_now[t])
    dist = dist[:, 0]; idx = np.where(np.isfinite(dist), idx[:, 0], 0)
    pairs = collections.Counter((a, b) for a, b, c in zip(name_now, name_old, close) if c and a != b)
    skin = {i for i, s in enumerate(sn) if 'Skin' in s or s.startswith('Skin_')}
    fix = {int(t): sn.index(b) for t, (a, b, c) in enumerate(zip(name_now, name_old, close)) if c and a != b and b in sn and int(now[t, 0]) not in skin}
    # the fix is applied on the source model (what copy_mesh_from_skeletal_mesh / copy_mesh_to edit): index it there
    src = np.array(d['source_now']) if d.get('source_now') else None; fix_src = {}
    if src is not None and len(fix):
        ds, js = tree.query(src[:, 1:], k=4, distance_upper_bound=0.05)
        for t in range(len(src)):
            if int(src[t, 0]) in skin: continue                    # skin triangles are the rollout's own
            cand = {sb[int(old[i, 0])] if int(old[i, 0]) < len(sb) else None for dd, i in zip(ds[t], js[t]) if np.isfinite(dd)}
            if len(cand) != 1: continue
            want = cand.pop()
            if want in sn and want not in [sn[i] for i in skin] and sn.index(want) != int(src[t, 0]): fix_src[t] = sn.index(want)
    # a write-back scramble moves whole slots in a closed permutation among slots that existed then and now; slots
    # added later by other work (e.g. Super90 factory parts) are intentional and never part of it
    dom = {}
    per_slot = collections.defaultdict(collections.Counter)
    for t in range(len(now)):
        if close[t] and int(now[t, 0]) not in skin: per_slot[name_now[t]][name_old[t]] += 1
    for x, cnt in per_slot.items():
        y, n_ = cnt.most_common(1)[0]
        if y != x and x in sb and y in sn and n_ >= .9 * sum(cnt.values()) and n_ >= 5: dom[x] = y
    perm = {}
    for x in dom:                                                   # keep only closed cycles
        seen_, c = [], x
        while c in dom and c not in seen_: seen_.append(c); c = dom[c]
        if c == x and len(seen_) >= 2: perm.update({k: dom[k] for k in seen_})
    fix_perm = {}
    if src is not None and perm:
        for t in range(len(src)):
            x = sn[int(src[t, 0])] if int(src[t, 0]) < len(sn) else None
            if x in perm: fix_perm[t] = sn.index(perm[x])
    report[f.stem] = dict(path=d['path'], total=len(now), matched=int(close.sum()), mismatched=len(fix), by_pair=[[a, b, n] for (a, b), n in pairs.most_common(8)],
                          source_triangles=0 if src is None else len(src), fix_source=fix_src, permutation=perm, fix_source_perm=fix_perm)
    print('%-60s triangles %6d matched %6d wrong material %5d | %s' % (d['path'].split('/')[-1][:60], len(now), close.sum(), len(fix), pairs.most_common(4)))
(R / DST).write_text(json.dumps(report))
